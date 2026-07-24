import csv
import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from PIL import Image

from weon_eval.budget import KeyAllowance
from weon_eval.budget_search import run_budget_search
from weon_eval.openrouter import GenerationResult
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS
from weon_eval.search_methods import SEARCH_METHODS
from weon_eval.vlm import JsonResult


def _jpeg() -> bytes:
    output = BytesIO()
    Image.new("RGB", (24, 32), "olive").save(output, format="JPEG")
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


def test_budget_search_runs_d01_d03_only_and_stops_at_floor(tmp_path: Path) -> None:
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
    cases.append(
        {
            "id": "H01",
            "split": "holdout",
            "model": str(tmp_path / "missing-model.png"),
            "environment": str(tmp_path / "missing-environment.png"),
            "garments": [str(tmp_path / "missing-garment.png")],
        }
    )
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps({"cases": cases}))
    prompt_path = tmp_path / "baseline.txt"
    prompt_path.write_text("Create scene.\n{garment_roles}\n")

    remaining = Decimal("10.20")
    generated_prompts: list[str] = []

    def allowance_getter(api_key: str) -> KeyAllowance:
        assert api_key == "secret"
        return KeyAllowance(remaining, Decimal("20"), Decimal("20") - remaining)

    def generator(payload: dict[str, object], api_key: str) -> GenerationResult:
        nonlocal remaining
        assert api_key == "secret"
        generated_prompts.append(str(payload["prompt"]))
        remaining -= Decimal("0.04")
        return GenerationResult(
            image=_jpeg(),
            cost_usd=Decimal("0.04"),
            media_type="image/jpeg",
        )

    def requester(**kwargs: object) -> JsonResult:
        nonlocal remaining
        remaining -= Decimal("0.002")
        scores = {dimension: 1.0 for dimension in ATTRIBUTE_DIMENSIONS}
        image_paths = tuple(kwargs["image_paths"])  # type: ignore[arg-type]
        case_id = Path(image_paths[0]).name.split("-")[0]
        if case_id == "D03":
            scores["print_logo"] = -1.0
        return JsonResult(
            data={"candidate_1": {"scores": scores, "summary": "fixed"}},
            cost_usd=Decimal("0.002"),
            latency_seconds=0.2,
        )

    output_root = tmp_path / "outputs" / "budget-search"
    result = run_budget_search(
        cases_path=cases_path,
        prompt_path=prompt_path,
        api_key="secret",
        output_root=output_root,
        methods=(SEARCH_METHODS[0],),
        generator=generator,
        requester=requester,
        allowance_getter=allowance_getter,
        clock=lambda: 1.0,
        max_paid_requests=100,
    )

    assert result == output_root
    rows = list(csv.DictReader((output_root / "results.csv").open()))
    assert [row["case_id"] for row in rows] == ["D01", "D02", "D03"]
    assert all(row["method"] == "lite_direct" for row in rows)
    assert len(generated_prompts) == 3
    assert remaining == Decimal("10.074")
    summary = json.loads((output_root / "search_summary.json").read_text())
    assert summary["stop_reason"] == "floor_guard"
    assert summary["ending_allowance_usd"] == "10.074"
    assert summary["paid_requests"] == 6
    assert summary["holdout_requests"] == 0
    assert summary["winner"] == "lite_direct"
    review_rows = list(csv.DictReader((output_root / "review_scores.csv").open()))
    assert len(review_rows) == 3
    assert all(row["reviewer"] == "" for row in review_rows)
