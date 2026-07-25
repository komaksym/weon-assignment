import csv
import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from PIL import Image

from weon_eval.development import run_development
from weon_eval.openrouter import GenerationResult
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS
from weon_eval.vlm import JsonResult


def _jpeg(color: str) -> bytes:
    output = BytesIO()
    Image.new("RGB", (24, 32), color).save(output, format="JPEG")
    return output.getvalue()


def _write_case_images(root: Path, case_id: str) -> dict[str, str]:
    paths = {
        "model": root / f"{case_id}-model.png",
        "environment": root / f"{case_id}-environment.png",
        "garment": root / f"{case_id}-garment.png",
    }
    for path in paths.values():
        Image.new("RGB", (32, 24), "olive").save(path)
    return {key: str(path) for key, path in paths.items()}


def test_run_development_executes_nine_generations_and_no_holdouts(tmp_path: Path) -> None:
    cases = []
    for case_id in ("D01", "D02", "D03"):
        paths = _write_case_images(tmp_path, case_id)
        cases.append(
            {
                "id": case_id,
                "split": "development",
                "model": paths["model"],
                "environment": paths["environment"],
                "garments": [paths["garment"]],
            }
        )
    holdout = _write_case_images(tmp_path, "H01")
    cases.append(
        {
            "id": "H01",
            "split": "holdout",
            "model": holdout["model"],
            "environment": holdout["environment"],
            "garments": [holdout["garment"]],
        }
    )
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps({"cases": cases}))
    prompt_path = tmp_path / "baseline.txt"
    prompt_path.write_text("Create scene.\n{garment_roles}\n")

    generation_prompts: list[str] = []

    def generator(payload: dict[str, object], api_key: str) -> GenerationResult:
        assert api_key == "secret"
        generation_prompts.append(str(payload["prompt"]))
        color = "red" if len(generation_prompts) % 3 == 0 else "blue"
        return GenerationResult(
            image=_jpeg(color),
            cost_usd=Decimal("0.01"),
            media_type="image/jpeg",
        )

    request_names: list[str] = []

    def requester(**kwargs: object) -> JsonResult:
        name = str(kwargs["schema_name"])
        request_names.append(name)
        if name == "garment_attributes":
            return JsonResult(
                data={
                    "attributes": {
                        dimension: f"visible {dimension}"
                        for dimension in ATTRIBUTE_DIMENSIONS
                    }
                },
                cost_usd=Decimal("0.001"),
                latency_seconds=0.1,
            )
        candidate = {
            "scores": {dimension: 0.5 for dimension in ATTRIBUTE_DIMENSIONS},
            "summary": "partial",
        }
        better = {
            "scores": {dimension: 1 for dimension in ATTRIBUTE_DIMENSIONS},
            "summary": "best",
        }
        return JsonResult(
            data={"baseline": candidate, "structured_a": candidate, "structured_b": better},
            cost_usd=Decimal("0.002"),
            latency_seconds=0.2,
        )

    output_root = tmp_path / "outputs" / "development"
    result = run_development(
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
    assert len(generation_prompts) == 9
    assert request_names.count("garment_attributes") == 3
    assert request_names.count("garment_comparison") == 3
    assert all("H01" not in prompt for prompt in generation_prompts)
    assert sum("hard visual constraints" in prompt for prompt in generation_prompts) == 6

    rows = list(csv.DictReader((output_root / "results.csv").open()))
    assert len(rows) == 9
    assert {row["strategy"] for row in rows} == {
        "baseline",
        "structured",
        "best_of_two",
    }
    assert all(
        row["candidate"] == "structured_b"
        for row in rows
        if row["strategy"] == "best_of_two"
    )
    summary = json.loads((output_root / "development_summary.json").read_text())
    assert summary["image_requests"] == 9
    assert summary["vlm_requests"] == 6
    assert summary["holdout_calls"] == 0
    assert summary["total_generation_cost_usd"] == "0.09"
    assert summary["total_selection_cost_usd"] == "0.006"
    assert summary["auto_winner"] == "best_of_two"
    for case_id in ("D01", "D02", "D03"):
        assert (output_root / case_id / "contact_sheet.jpg").exists()
        selection = json.loads(
            (output_root / case_id / "best_of_two" / "selection.json").read_text()
        )
        assert selection["selected"] == "structured_b"
