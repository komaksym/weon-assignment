from pathlib import Path

from weon_eval.cases import Case
from weon_eval.prompts import render_prompt


def test_render_prompt_lists_garment_roles(tmp_path: Path) -> None:
    template = tmp_path / "baseline.txt"
    template.write_text("Scene request.\n{garment_roles}\n")
    case = Case(
        id="D04",
        split="development",
        model=Path("model.png"),
        environment=Path("environment.png"),
        garments=(Path("shorts.png"), Path("sneakers.png")),
    )

    prompt = render_prompt(case, template)

    assert "Garment 1: shorts.png" in prompt
    assert "Garment 2: sneakers.png" in prompt
