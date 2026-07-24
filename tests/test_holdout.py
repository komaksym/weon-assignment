import csv
import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from weon_eval.holdout import run_holdouts
from weon_eval.openrouter import GenerationResult
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS
from weon_eval.vlm import JsonResult


def _jpeg() -> bytes:
    output = BytesIO()
    Image.new("RGB", (24, 32), "olive").save(output, format="JPEG")
    return output.getvalue()


def _write_images(root: Path, case_id: str) -> dict[str, str]:
    paths = {
        "model": root / f"{case_id}-model.png",
        "environment": root / f"{case_id}-environment.png",
        "garment": root / f"{case_id}-garment.png",
    }
    for path in paths.values():
        Image.new("RGB", (32, 24), "olive").save(path)
    return {key: str(path) for key, path in paths.items()}


def _write_cases(root: Path, entries: tuple[tuple[str, str], ...]) -> Path:
    cases = []
    for case_id, split in entries:
        paths = _write_images(root, case_id)
        cases.append(
            {
                "id": case_id,
                "split": split,
                "model": paths["model"],
                "environment": paths["environment"],
                "garments": [paths["garment"]],
            }
        )
    cases_path = root / "cases.json"
    cases_path.write_text(json.dumps({"cases": cases}))
    return cases_path


def _generator(payload: dict[str, object], api_key: str) -> GenerationResult:
    assert api_key == "secret"
    assert payload["n"] == 1
    return GenerationResult(
        image=_jpeg(),
        cost_usd=Decimal("0.03"),
        media_type="image/jpeg",
    )


def test_run_holdouts_executes_only_two_frozen_cases(tmp_path: Path) -> None:
    cases_path = _write_cases(
        tmp_path,
        (("D01", "development"), ("H01", "holdout"), ("H02", "holdout")),
    )
    prompt_path = tmp_path / "baseline.txt"
    prompt_path.write_text("Create scene.\n{garment_roles}\n")

    prompts: list[str] = []

    def generator(payload: dict[str, object], api_key: str) -> GenerationResult:
        prompts.append(str(payload["prompt"]))
        return _generator(payload, api_key)

    requests: list[tuple[str, tuple[Path, ...]]] = []

    def requester(**kwargs: object) -> JsonResult:
        requests.append(
            (
                str(kwargs["schema_name"]),
                tuple(kwargs["image_paths"]),  # type: ignore[arg-type]
            )
        )
        result = {
            "candidate_1": {
                "scores": {dimension: 0.5 for dimension in ATTRIBUTE_DIMENSIONS},
                "summary": "partial preservation",
            }
        }
        return JsonResult(
            data=result,
            cost_usd=Decimal("0.002"),
            latency_seconds=0.4,
        )

    output_root = tmp_path / "outputs" / "holdout"
    result = run_holdouts(
        cases_path=cases_path,
        prompt_path=prompt_path,
        api_key="secret",
        output_root=output_root,
        generator_model="generator",
        evaluator_model="evaluator",
        generator=generator,
        requester=requester,
    )

    assert result == output_root
    assert len(prompts) == 2
    assert all("D01" not in prompt for prompt in prompts)
    assert [name for name, _ in requests] == ["holdout_candidate", "holdout_candidate"]
    assert all(len(paths) == 2 for _, paths in requests)

    rows = list(csv.DictReader((output_root / "results.csv").open()))
    assert [row["case_id"] for row in rows] == ["H01", "H02"]
    review_rows = list(csv.DictReader((output_root / "review_scores.csv").open()))
    assert [row["case_id"] for row in review_rows] == ["H01", "H02"]
    assert all(row["reviewer"] == "" for row in review_rows)
    assert all(row["review_method"] == "" for row in review_rows)
    assert all(row["mean_review_score"] == "" for row in review_rows)
    assert not (output_root / "manual_scores.csv").exists()
    assert all(row["strategy"] == "baseline" for row in rows)
    assert all(row["mean_auto_score"] == "0.5" for row in rows)
    assert all(row["total_experiment_cost_usd"] == "0.032" for row in rows)

    summary = json.loads((output_root / "holdout_summary.json").read_text())
    assert summary["image_requests"] == 2
    assert summary["evaluation_requests"] == 2
    assert summary["development_requests"] == 0
    assert summary["automatic_retries"] == 0
    assert summary["total_experiment_cost_usd"] == "0.064"
    for case_id in ("H01", "H02"):
        contact_sheet = output_root / case_id / "contact_sheet.jpg"
        assert contact_sheet.exists()
        with Image.open(contact_sheet) as image:
            assert image.size == (1260, 582)
        crop = json.loads((output_root / case_id / "contact_sheet.json").read_text())
        assert crop["method"] == "frozen case-specific normalized garment-region crop"
        assert len(crop["pixel_box"]) == 4
        assert (output_root / case_id / "evaluation.json").exists()


def test_run_holdouts_rejects_invalid_footwear_na_before_aggregation(tmp_path: Path) -> None:
    cases_path = _write_cases(
        tmp_path,
        (("H01", "holdout"), ("H02", "holdout")),
    )
    prompt_path = tmp_path / "baseline.txt"
    prompt_path.write_text("Create scene.\n{garment_roles}\n")

    def requester(**kwargs: object) -> JsonResult:
        scores = {dimension: 1.0 for dimension in ATTRIBUTE_DIMENSIONS}
        scores["silhouette_length"] = -1.0
        return JsonResult(
            data={
                "candidate_1": {
                    "scores": scores,
                    "summary": "silhouette is not applicable for shoes",
                }
            },
            cost_usd=Decimal("0.002"),
            latency_seconds=0.4,
        )

    output_root = tmp_path / "outputs" / "holdout"
    with pytest.raises(ValueError, match="H01: evaluator returned invalid N/A applicability"):
        run_holdouts(
            cases_path=cases_path,
            prompt_path=prompt_path,
            api_key="secret",
            output_root=output_root,
            generator_model="generator",
            evaluator_model="evaluator",
            generator=_generator,
            requester=requester,
        )

    assert (output_root / "H01" / "evaluation.json").exists()
    assert not (output_root / "results.csv").exists()
