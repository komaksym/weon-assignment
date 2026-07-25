import pytest

from weon_eval.evaluation import validate_applicability_masks
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS


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
