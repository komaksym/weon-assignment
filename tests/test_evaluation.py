import pytest

from weon_eval.evaluation import (
    CANDIDATE_IDS,
    STRATEGIES,
    blinded_candidate_mapping,
    evaluation_prompt,
    evaluation_schema,
    strategy_candidate_ids,
    validate_applicability_masks,
)
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS


def test_evaluator_uses_opaque_stable_candidate_ids() -> None:
    mapping = blinded_candidate_mapping("D01")

    assert mapping == blinded_candidate_mapping("D01")
    assert set(mapping) == set(CANDIDATE_IDS)
    assert set(mapping.values()) == set(STRATEGIES)
    assert strategy_candidate_ids(mapping) == {
        strategy: candidate_id for candidate_id, strategy in mapping.items()
    }

    schema = evaluation_schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    assert set(properties) == set(CANDIDATE_IDS)
    assert not set(STRATEGIES).intersection(properties)

    prompt = evaluation_prompt()
    assert all(candidate_id in prompt for candidate_id in CANDIDATE_IDS)
    assert all(strategy not in prompt for strategy in STRATEGIES)


def test_validate_applicability_masks_rejects_candidate_specific_na() -> None:
    baseline = {dimension: 1.0 for dimension in ATTRIBUTE_DIMENSIONS}
    structured_a = dict(baseline)
    structured_b = dict(baseline)
    structured_a["print_logo"] = -1.0

    with pytest.raises(ValueError, match="inconsistent N/A applicability"):
        validate_applicability_masks(baseline, structured_a, structured_b)


def test_validate_applicability_masks_accepts_shared_na() -> None:
    baseline = {dimension: 1.0 for dimension in ATTRIBUTE_DIMENSIONS}
    structured_a = dict(baseline)
    structured_b = dict(baseline)
    for scores in (baseline, structured_a, structured_b):
        scores["print_logo"] = -1.0

    validate_applicability_masks(baseline, structured_a, structured_b)
