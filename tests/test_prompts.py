from pathlib import Path

import pytest

from weon_eval.cases import Case
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS, render_prompt, render_structured_prompt


def _case() -> Case:
    return Case(
        id="D04",
        split="development",
        model=Path("model.png"),
        environment=Path("environment.png"),
        garments=(Path("shorts.png"), Path("sneakers.png")),
    )


def test_render_prompt_lists_garment_roles(tmp_path: Path) -> None:
    template = tmp_path / "baseline.txt"
    template.write_text("Scene request.\n{garment_roles}\n")

    prompt = render_prompt(_case(), template)

    assert "Garment 1: shorts.png" in prompt
    assert "Garment 2: sneakers.png" in prompt


def test_render_structured_prompt_adds_all_visible_constraints(tmp_path: Path) -> None:
    template = tmp_path / "baseline.txt"
    template.write_text("Scene request.\n{garment_roles}\n")
    attributes = {dimension: f"visible {dimension}" for dimension in ATTRIBUTE_DIMENSIONS}

    prompt = render_structured_prompt(_case(), template, attributes)

    assert "color: visible color" in prompt
    assert "construction details: visible construction_details" in prompt
    assert "hard visual constraints" in prompt


def test_render_structured_prompt_rejects_missing_attribute(tmp_path: Path) -> None:
    template = tmp_path / "baseline.txt"
    template.write_text("{garment_roles}\n")

    with pytest.raises(ValueError, match="missing garment attributes"):
        render_structured_prompt(_case(), template, {"color": "olive"})
