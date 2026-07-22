"""Render experiment prompts."""

from pathlib import Path

from weon_eval.cases import Case


def render_prompt(case: Case, template_path: Path) -> str:
    """Render a prompt with explicit garment reference roles."""

    template = template_path.read_text()
    roles = "\n".join(
        f"Garment {index}: {path.name}" for index, path in enumerate(case.garments, start=1)
    )
    try:
        return template.format(garment_roles=roles)
    except KeyError as exc:
        raise ValueError(f"unknown prompt placeholder: {exc.args[0]}") from exc
