"""Render experiment prompts."""

from collections.abc import Mapping
from pathlib import Path

from weon_eval.cases import Case

ATTRIBUTE_DIMENSIONS = (
    "color",
    "print_logo",
    "silhouette_length",
    "construction_details",
    "texture_material",
    "presence",
)


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


def render_structured_prompt(
    case: Case,
    template_path: Path,
    attributes: Mapping[str, str],
) -> str:
    """Append fixed visible garment attributes to the baseline prompt."""

    missing = [dimension for dimension in ATTRIBUTE_DIMENSIONS if not attributes.get(dimension)]
    if missing:
        raise ValueError(f"missing garment attributes: {', '.join(missing)}")
    lines = [
        f"- {dimension.replace('_', ' ')}: {attributes[dimension]}"
        for dimension in ATTRIBUTE_DIMENSIONS
    ]
    attribute_text = "\n".join(lines)
    return (
        f"{render_prompt(case, template_path).rstrip()}\n\n"
        "Visible garment constraints extracted from the packshot:\n"
        f"{attribute_text}\n\n"
        "Treat these as hard visual constraints. Preserve only details visible in the packshot; "
        "do not invent missing branding or construction."
    )
