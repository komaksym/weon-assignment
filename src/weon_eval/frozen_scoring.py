"""Immutable single-candidate scoring used by the budgeted search."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from weon_eval.evaluation import JsonRequester, mean_score, parse_scores, summary_text
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS
from weon_eval.vlm import request_json

DEFAULT_EVALUATOR_MODEL = "openai/gpt-4.1-mini"
FROZEN_APPLICABLE_DIMENSIONS = {
    "D01": frozenset(ATTRIBUTE_DIMENSIONS),
    "D02": frozenset(ATTRIBUTE_DIMENSIONS),
    "D03": frozenset(dimension for dimension in ATTRIBUTE_DIMENSIONS if dimension != "print_logo"),
}
FROZEN_EVALUATION_PROMPT = (
    "Image order: garment packshot(s), candidate_1. The candidate identity is opaque. "
    "Judge candidate_1 only against the garment packshot on color, print/logo, "
    "silhouette/length, construction details, texture/material, and garment presence. "
    "Use 1 for preserved, 0.5 for partial, 0 for drifted, and -1 only when the source "
    "attribute is genuinely not applicable. Do not reward overall aesthetics."
)


@dataclass(frozen=True)
class FrozenScore:
    """Validated frozen-rubric result and request measurements."""

    scores: dict[str, float]
    mean: float
    summary: str
    cost_usd: Decimal | None
    latency_seconds: float


def frozen_candidate_schema() -> dict[str, object]:
    """Return the immutable JSON schema for one opaque candidate."""

    score_properties = {
        dimension: {"type": "number", "enum": [-1, 0, 0.5, 1]}
        for dimension in ATTRIBUTE_DIMENSIONS
    }
    candidate = {
        "type": "object",
        "properties": {
            "scores": {
                "type": "object",
                "properties": score_properties,
                "required": list(ATTRIBUTE_DIMENSIONS),
                "additionalProperties": False,
            },
            "summary": {"type": "string", "minLength": 1},
        },
        "required": ["scores", "summary"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"candidate_1": candidate},
        "required": ["candidate_1"],
        "additionalProperties": False,
    }


def validate_source_applicability(case_id: str, scores: Mapping[str, float]) -> None:
    """Reject candidate-specific N/A choices that violate the frozen source mask."""

    try:
        applicable = FROZEN_APPLICABLE_DIMENSIONS[case_id]
    except KeyError as exc:
        raise ValueError(f"no frozen applicability mask for {case_id}") from exc
    expected_na = set(ATTRIBUTE_DIMENSIONS) - set(applicable)
    actual_na = {dimension for dimension, score in scores.items() if score < 0}
    if actual_na != expected_na:
        raise ValueError(
            f"{case_id}: evaluator returned invalid N/A applicability; "
            f"expected {sorted(expected_na)}, got {sorted(actual_na)}"
        )


def score_candidate(
    *,
    case_id: str,
    garment_paths: Sequence[Path],
    candidate_path: Path,
    raw_output_path: Path,
    api_key: str,
    evaluator_model: str = DEFAULT_EVALUATOR_MODEL,
    requester: JsonRequester = request_json,
) -> FrozenScore:
    """Score one candidate, persisting raw evaluator JSON before validation."""

    result = requester(
        model=evaluator_model,
        prompt=FROZEN_EVALUATION_PROMPT,
        image_paths=(*garment_paths, candidate_path),
        schema_name="budget_search_candidate",
        schema=frozen_candidate_schema(),
        api_key=api_key,
    )
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_output_path.write_text(
        json.dumps(
            {
                "candidate_id": "candidate_1",
                "evaluation": result.data,
                "evaluator_model": evaluator_model,
                "prompt": FROZEN_EVALUATION_PROMPT,
                "cost_usd": str(result.cost_usd) if result.cost_usd is not None else None,
                "latency_seconds": result.latency_seconds,
            },
            indent=2,
        )
        + "\n"
    )
    scores = parse_scores(result.data, "candidate_1")
    validate_source_applicability(case_id, scores)
    return FrozenScore(
        scores=scores,
        mean=mean_score(scores),
        summary=summary_text(result.data, "candidate_1"),
        cost_usd=result.cost_usd,
        latency_seconds=result.latency_seconds,
    )
