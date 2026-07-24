import json
from decimal import Decimal
from pathlib import Path

import pytest

from weon_eval.frozen_scoring import (
    FROZEN_EVALUATION_PROMPT,
    score_candidate,
)
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS
from weon_eval.vlm import JsonResult


def _requester_with(scores: dict[str, float]):
    def requester(**kwargs: object) -> JsonResult:
        assert kwargs["model"] == "openai/gpt-4.1-mini"
        assert kwargs["prompt"] == FROZEN_EVALUATION_PROMPT
        assert kwargs["schema_name"] == "budget_search_candidate"
        return JsonResult(
            data={"candidate_1": {"scores": scores, "summary": "fixed rubric"}},
            cost_usd=Decimal("0.002"),
            latency_seconds=0.4,
        )

    return requester


def test_score_candidate_accepts_frozen_d03_na_and_persists_raw(tmp_path: Path) -> None:
    scores = {dimension: 1.0 for dimension in ATTRIBUTE_DIMENSIONS}
    scores["print_logo"] = -1.0
    raw_path = tmp_path / "evaluation.json"

    result = score_candidate(
        case_id="D03",
        garment_paths=(tmp_path / "garment.jpg",),
        candidate_path=tmp_path / "candidate.jpg",
        raw_output_path=raw_path,
        api_key="secret",
        requester=_requester_with(scores),
    )

    assert result.mean == 1.0
    raw = json.loads(raw_path.read_text())
    assert raw["evaluation"]["candidate_1"]["scores"]["print_logo"] == -1.0
    assert raw["prompt"] == FROZEN_EVALUATION_PROMPT


def test_score_candidate_rejects_d02_candidate_specific_na_after_raw_persist(
    tmp_path: Path,
) -> None:
    scores = {dimension: 1.0 for dimension in ATTRIBUTE_DIMENSIONS}
    scores["silhouette_length"] = -1.0
    raw_path = tmp_path / "evaluation.json"

    with pytest.raises(ValueError, match="D02: evaluator returned invalid N/A"):
        score_candidate(
            case_id="D02",
            garment_paths=(tmp_path / "garment.jpg",),
            candidate_path=tmp_path / "candidate.jpg",
            raw_output_path=raw_path,
            api_key="secret",
            requester=_requester_with(scores),
        )

    assert raw_path.exists()
