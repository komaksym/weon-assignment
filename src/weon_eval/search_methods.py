"""Predeclared garment-consistency methods and deterministic references."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from weon_eval.cases import Case
from weon_eval.runner import OUTPUT_ASPECT_RATIO, OUTPUT_RESOLUTION, prepare_reference


@dataclass(frozen=True)
class SearchMethod:
    """One immutable generation method in the round-robin search."""

    name: str
    model: str
    prompt_kind: str
    reference_mode: str
    passes: int
    generation_reserve_usd: Decimal


SEARCH_METHODS = (
    SearchMethod("lite_direct", "google/gemini-3.1-flash-lite-image", "baseline", "direct", 1, Decimal("0.06")),
    SearchMethod("lite_identity_prompt", "google/gemini-3.1-flash-lite-image", "identity", "direct", 1, Decimal("0.06")),
    SearchMethod("lite_detail_board", "google/gemini-3.1-flash-lite-image", "baseline", "detail_board", 1, Decimal("0.06")),
    SearchMethod("lite_two_pass_repair", "google/gemini-3.1-flash-lite-image", "baseline", "direct", 2, Decimal("0.06")),
    SearchMethod("nano25_direct", "google/gemini-2.5-flash-image", "baseline", "direct", 1, Decimal("0.10")),
    SearchMethod("nano31_direct", "google/gemini-3.1-flash-image", "baseline", "direct", 1, Decimal("0.18")),
    SearchMethod("nano31_detail_board", "google/gemini-3.1-flash-image", "baseline", "detail_board", 1, Decimal("0.18")),
    SearchMethod("seedream_direct", "bytedance-seed/seedream-4.5", "baseline", "direct", 1, Decimal("0.06")),
    SearchMethod("seedream_detail_board", "bytedance-seed/seedream-4.5", "baseline", "detail_board", 1, Decimal("0.06")),
    SearchMethod("gpt_image_1_mini_direct", "openai/gpt-image-1-mini", "baseline", "direct", 1, Decimal("0.30")),
    SearchMethod("gpt_image_1_mini_detail_board", "openai/gpt-image-1-mini", "baseline", "detail_board", 1, Decimal("0.30")),
    SearchMethod("gpt_image_2_direct", "openai/gpt-image-2", "baseline", "direct", 1, Decimal("0.80")),
    SearchMethod("gpt_image_2_detail_board", "openai/gpt-image-2", "baseline", "detail_board", 1, Decimal("0.80")),
    SearchMethod("nano31_two_pass_repair", "google/gemini-3.1-flash-image", "baseline", "direct", 2, Decimal("0.18")),
)

IDENTITY_PRIORITY_SUFFIX = """

PRODUCT-IDENTITY PRIORITY:
The garment must remain the exact referenced product, not merely the same category.
Prioritize readable branding, exact panel and pocket geometry, closures, seams, sole/toe shape,
material boundaries, texture, and color over creative styling. Do not simplify, redesign,
substitute, mirror, move, add, or remove product-defining details. Keep the person and setting
natural, but sacrifice aesthetic embellishment before sacrificing garment fidelity.
""".strip()

REPAIR_PROMPT = """Edit reference 1 rather than creating a new composition.
Keep the person's identity, face, body, pose, framing, lighting, camera, and background unchanged.
Use the remaining garment packshot reference(s) as the sole product truth. Correct only the worn
garment so it matches the exact source product: branding/text, color, silhouette, length, panels,
pockets, seams, closures, zippers, buttons, sole/toe geometry, material boundaries, and texture.
Do not add accessories, alter the person, restyle the scene, or invent hidden details."""


def method_prompt(method: SearchMethod, baseline_prompt: str) -> str:
    """Return the predeclared prompt for a method."""

    if method.prompt_kind == "baseline":
        return baseline_prompt
    if method.prompt_kind == "identity":
        return f"{baseline_prompt.rstrip()}\n\n{IDENTITY_PRIORITY_SUFFIX}\n"
    raise ValueError(f"unsupported prompt kind: {method.prompt_kind}")


def _rgb(path: Path) -> Image.Image:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
    background = Image.new("RGBA", image.size, "white")
    background.alpha_composite(image)
    return background.convert("RGB")


def _crop(image: Image.Image, top: float, bottom: float) -> Image.Image:
    height = image.height
    return image.crop((0, round(top * height), image.width, round(bottom * height)))


def _panel(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    contained = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
    panel = Image.new("RGB", size, "white")
    panel.paste(contained, ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2))
    return panel


def create_detail_board(garment_path: Path, output_path: Path) -> Path:
    """Create a deterministic full/top/center/bottom garment reference board."""

    image = _rgb(garment_path)
    panels = (
        ("full", image),
        ("upper detail", _crop(image, 0.0, 0.60)),
        ("center detail", _crop(image, 0.20, 0.80)),
        ("lower detail", _crop(image, 0.40, 1.0)),
    )
    panel_size = (512, 472)
    label_height = 40
    board = Image.new("RGB", (1024, 1024), "white")
    draw = ImageDraw.Draw(board)
    for index, (label, panel_image) in enumerate(panels):
        x = (index % 2) * panel_size[0]
        y = (index // 2) * (panel_size[1] + label_height)
        board.paste(_panel(panel_image, panel_size), (x, y))
        draw.text((x + 12, y + panel_size[1] + 10), label, fill="black")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    board.save(output_path, format="JPEG", quality=92, optimize=True)
    return output_path


def method_reference_paths(case: Case, method: SearchMethod, work_dir: Path) -> tuple[Path, ...]:
    """Return person/environment/garment references for one predeclared method."""

    if method.reference_mode == "direct":
        return case.reference_paths
    if method.reference_mode == "detail_board":
        board = create_detail_board(case.garments[0], work_dir / "garment-detail-board.jpg")
        return (case.model, case.environment, board)
    raise ValueError(f"unsupported reference mode: {method.reference_mode}")


def build_payload(
    *,
    model: str,
    prompt: str,
    reference_paths: tuple[Path, ...],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Build one unified Images API payload from arbitrary ordered paths."""

    references = tuple(prepare_reference(path) for path in reference_paths)
    payload: dict[str, object] = {
        "model": model,
        "prompt": prompt,
        "input_references": [
            {"type": "image_url", "image_url": {"url": reference.data_url}}
            for reference in references
        ],
        "n": 1,
        "aspect_ratio": OUTPUT_ASPECT_RATIO,
        "resolution": OUTPUT_RESOLUTION,
    }
    return payload, [reference.metadata() for reference in references]
