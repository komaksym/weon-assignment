import csv
import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from weon_eval.budget import KeyAllowance
from weon_eval.openrouter import GenerationResult
from weon_eval.promotion_cli import build_parser
from weon_eval.promotion_search import (
    PROMOTION_METHODS,
    parse_selector,
    run_promotion_search,
    selector_mapping,
)
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS
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


def test_promotion_method_order_is_frozen() -> None:
    assert [method.name for method in PROMOTION_METHODS] == [
        "duplicate_garment_best_of_two",
        "identity_tight_crop_best_of_two",
        "duplicate_garment_repair",
        "identity_tight_crop_repair",
    ]
    assert [method.base_method.name for method in PROMOTION_METHODS] == [
        "lite_duplicate_garment",
        "lite_identity_tight_crop",
        "lite_duplicate_garment",
        "lite_identity_tight_crop",
    ]


def test_selector_mapping_is_deterministic_and_opaque() -> None:
    first = selector_mapping("duplicate_garment_best_of_two", "D01", 1)
    second = selector_mapping("duplicate_garment_best_of_two", "D01", 1)

    assert first == second
    assert set(first) == {"candidate_1", "candidate_2"}
    assert set(first.values()) == {"a", "b"}


def test_selector_tie_must_resolve_to_candidate_one() -> None:
    with pytest.raises(ValueError, match="ties must resolve"):
        parse_selector(
            {
                "winner": "candidate_2",
                "tie": True,
                "summary": "indistinguishable",
            }
        )


def test_promotion_cli_defaults_are_frozen() -> None:
    args = build_parser().parse_args([])

    assert args.output == Path("outputs/promotion-search")
    assert args.floor_usd == Decimal("0.30")
    assert args.max_paid_requests == 300


def test_repair_promotion_runs_development_cases_only_and_stops_at_floor(
    tmp_path: Path,
) -> None:
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

    remaining = Decimal("0.80")
    generated_prompts: list[str] = []

    def allowance_getter(api_key: str) -> KeyAllowance:
        assert api_key == "secret"
        return KeyAllowance(remaining, Decimal("10"), Decimal("10") - remaining)

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

    output_root = tmp_path / "outputs" / "promotion"
    result = run_promotion_search(
        cases_path=cases_path,
        prompt_path=prompt_path,
        api_key="secret",
        output_root=output_root,
        floor_usd=Decimal("0.50"),
        methods=(PROMOTION_METHODS[2],),
        generator=generator,
        requester=requester,
        allowance_getter=allowance_getter,
        clock=lambda: 1.0,
        max_paid_requests=100,
    )

    assert result == output_root
    rows = list(csv.DictReader((output_root / "results.csv").open()))
    assert [row["case_id"] for row in rows] == ["D01", "D02", "D03"]
    assert all(row["method"] == "duplicate_garment_repair" for row in rows)
    assert len(generated_prompts) == 6
    assert remaining == Decimal("0.554")
    summary = json.loads((output_root / "search_summary.json").read_text())
    assert summary["stop_reason"] == "floor_guard"
    assert summary["paid_requests"] == 9
    assert summary["holdout_requests"] == 0
    assert summary["winner"] == "duplicate_garment_repair"
