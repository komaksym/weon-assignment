"""Schemas and validation for garment-attribute VLM judgments."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from itertools import permutations
from pathlib import Path
from typing import Protocol

from weon_eval.prompts import ATTRIBUTE_DIMENSIONS
from weon_eval.vlm import JsonResult

_ALLOWED_SCORES = {-1.0, 0.0, 0.5, 1.0}
CANDIDATE_IDS = ("candidate_1", "candidate_2", "candidate_3")
STRATEGIES = ("baseline", "structured_a", "structured_b")


class JsonRequester(Protocol):
    """Callable boundary used for testable VLM requests."""

    def __call__(
        self,
        *,
        model: str,
        prompt: str,
        image_paths: Sequence[Path],
        schema_name: str,
        schema: Mapping[str, object],
        api_key: str,
    ) -> JsonResult: ...


def attribute_schema() -> dict[str, object]:
    properties = {
        dimension: {"type": "string", "minLength": 1}
        for dimension in ATTRIBUTE_DIMENSIONS
    }
    return {
        "type": "object",
        "properties": {
            "attributes": {
                "type": "object",
                "properties": properties,
                "required": list(ATTRIBUTE_DIMENSIONS),
                "additionalProperties": False,
            }
        },
        "required": ["attributes"],
        "additionalProperties": False,
    }


def _candidate_schema() -> dict[str, object]:
    scores = {
        dimension: {"type": "number", "enum": [-1, 0, 0.5, 1]}
        for dimension in ATTRIBUTE_DIMENSIONS
    }
    return {
        "type": "object",
        "properties": {
            "scores": {
                "type": "object",
                "properties": scores,
                "required": list(ATTRIBUTE_DIMENSIONS),
                "additionalProperties": False,
            },
            "summary": {"type": "string", "minLength": 1},
        },
        "required": ["scores", "summary"],
        "additionalProperties": False,
    }


def evaluation_schema() -> dict[str, object]:
    candidate = _candidate_schema()
    return {
        "type": "object",
        "properties": {candidate_id: candidate for candidate_id in CANDIDATE_IDS},
        "required": list(CANDIDATE_IDS),
        "additionalProperties": False,
    }


def evaluation_prompt() -> str:
    """Describe the rubric without exposing treatment identity."""

    return (
        "Image order: garment packshot(s), candidate_1, candidate_2, candidate_3. "
        "The candidate IDs are opaque. Judge every candidate only against the garment "
        "packshot on color, print/logo, silhouette/length, construction details, "
        "texture/material, and garment presence. Use 1 for preserved, 0.5 for partial, "
        "0 for drifted, and -1 only when the source attribute is genuinely not applicable."
    )


def blinded_candidate_mapping(case_id: str) -> dict[str, str]:
    """Map opaque IDs to strategies using a stable case-specific permutation."""

    orders = tuple(permutations(STRATEGIES))
    digest = hashlib.sha256(case_id.encode()).digest()
    index = int.from_bytes(digest[:2], "big") % len(orders)
    return dict(zip(CANDIDATE_IDS, orders[index], strict=True))


def strategy_candidate_ids(mapping: Mapping[str, str]) -> dict[str, str]:
    """Invert and validate an opaque candidate mapping."""

    if set(mapping) != set(CANDIDATE_IDS) or set(mapping.values()) != set(STRATEGIES):
        raise ValueError("invalid blinded candidate mapping")
    return {strategy: candidate_id for candidate_id, strategy in mapping.items()}


def parse_attributes(data: Mapping[str, object]) -> dict[str, str]:
    raw = data.get("attributes")
    if not isinstance(raw, dict):
        raise ValueError("attribute evaluator returned no attributes")
    attributes: dict[str, str] = {}
    for dimension in ATTRIBUTE_DIMENSIONS:
        value = raw.get(dimension)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"attribute evaluator returned invalid {dimension}")
        attributes[dimension] = value.strip()
    return attributes


def parse_scores(data: Mapping[str, object], candidate: str) -> dict[str, float]:
    raw_candidate = data.get(candidate)
    if not isinstance(raw_candidate, dict):
        raise ValueError(f"evaluator returned no {candidate} result")
    raw_scores = raw_candidate.get("scores")
    if not isinstance(raw_scores, dict):
        raise ValueError(f"evaluator returned no {candidate} scores")
    scores: dict[str, float] = {}
    for dimension in ATTRIBUTE_DIMENSIONS:
        raw_score = raw_scores.get(dimension)
        if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
            raise ValueError(f"evaluator returned invalid {candidate} {dimension} score")
        score = float(raw_score)
        if score not in _ALLOWED_SCORES:
            raise ValueError(f"evaluator returned unsupported score: {score}")
        scores[dimension] = score
    return scores


def validate_applicability_masks(*candidate_scores: Mapping[str, float]) -> None:
    """Require source-level N/A dimensions to be identical for every candidate."""

    if not candidate_scores:
        raise ValueError("no candidate scores provided")
    expected = {
        dimension
        for dimension in ATTRIBUTE_DIMENSIONS
        if candidate_scores[0][dimension] < 0
    }
    for scores in candidate_scores[1:]:
        actual = {
            dimension
            for dimension in ATTRIBUTE_DIMENSIONS
            if scores[dimension] < 0
        }
        if actual != expected:
            raise ValueError("evaluator returned inconsistent N/A applicability")


def mean_score(scores: Mapping[str, float]) -> float:
    """Average applicable 0/0.5/1 scores, ignoring -1 (N/A)."""

    applicable = [score for score in scores.values() if score >= 0]
    if not applicable:
        raise ValueError("candidate has no applicable evaluation dimensions")
    return sum(applicable) / len(applicable)


def choose_best(structured_a: Mapping[str, float], structured_b: Mapping[str, float]) -> str:
    """Select the higher VLM score, breaking ties toward candidate A."""

    if mean_score(structured_a) >= mean_score(structured_b):
        return "structured_a"
    return "structured_b"


def summary_text(data: Mapping[str, object], candidate: str) -> str:
    raw = data.get(candidate)
    if not isinstance(raw, dict) or not isinstance(raw.get("summary"), str):
        raise ValueError(f"evaluator returned no {candidate} summary")
    return str(raw["summary"])
