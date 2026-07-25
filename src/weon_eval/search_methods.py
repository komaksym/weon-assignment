"""Predeclared garment-consistency methods and deterministic references."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

from PIL import Image, ImageDraw, ImageOps

from weon_eval.cases import Case
from weon_eval.runner import OUTPUT_ASPECT_RATIO, OUTPUT_RESOLUTION, prepare_reference


@dataclass(frozen=True)
class SearchMethod:
    """One immutable generation method in a round-robin search."""

    name: str
    model: str
    prompt_kind: str
    reference_mode: str
    passes: int
    generation_reserve_usd: Decimal


def _method(
    name: str,
    model: str,
    prompt_kind: str,
    reference_mode: str,
    passes: int,
    reserve: str,
) -> SearchMethod:
    return SearchMethod(
        name=name,
        model=model,
        prompt_kind=prompt_kind,
        reference_mode=reference_mode,
        passes=passes,
        generation_reserve_usd=Decimal(reserve),
    )


SEARCH_METHODS = (
    _method(
        "lite_direct",
        "google/gemini-3.1-flash-lite-image",
        "baseline",
        "direct",
        1,
        "0.06",
    ),
    _method(
        "lite_identity_prompt",
        "google/gemini-3.1-flash-lite-image",
        "identity",
        "direct",
        1,
        "0.06",
    ),
    _method(
        "lite_detail_board",
        "google/gemini-3.1-flash-lite-image",
        "baseline",
        "detail_board",
        1,
        "0.06",
    ),
    _method(
        "lite_two_pass_repair",
        "google/gemini-3.1-flash-lite-image",
        "baseline",
        "direct",
        2,
        "0.06",
    ),
    _method(
        "nano25_direct",
        "google/gemini-2.5-flash-image",
        "baseline",
        "direct",
        1,
        "0.10",
    ),
    _method(
        "nano31_direct",
        "google/gemini-3.1-flash-image",
        "baseline",
        "direct",
        1,
        "0.18",
    ),
    _method(
        "nano31_detail_board",
        "google/gemini-3.1-flash-image",
        "baseline",
        "detail_board",
        1,
        "0.18",
    ),
    _method(
        "seedream_direct",
        "bytedance-seed/seedream-4.5",
        "baseline",
        "direct",
        1,
        "0.06",
    ),
    _method(
        "seedream_detail_board",
        "bytedance-seed/seedream-4.5",
        "baseline",
        "detail_board",
        1,
        "0.06",
    ),
    _method(
        "gpt_image_1_mini_direct",
        "openai/gpt-image-1-mini",
        "baseline",
        "direct",
        1,
        "0.30",
    ),
    _method(
        "gpt_image_1_mini_detail_board",
        "openai/gpt-image-1-mini",
        "baseline",
        "detail_board",
        1,
        "0.30",
    ),
    _method(
        "gpt_image_2_direct",
        "openai/gpt-image-2",
        "baseline",
        "direct",
        1,
        "0.80",
    ),
    _method(
        "gpt_image_2_detail_board",
        "openai/gpt-image-2",
        "baseline",
        "detail_board",
        1,
        "0.80",
    ),
    _method(
        "nano31_two_pass_repair",
        "google/gemini-3.1-flash-image",
        "baseline",
        "direct",
        2,
        "0.18",
    ),
)

TARGETED_METHODS = (
    _method(
        "lite_identity_negative",
        "google/gemini-3.1-flash-lite-image",
        "identity_negative",
        "direct",
        1,
        "0.06",
    ),
    _method(
        "lite_tight_crop",
        "google/gemini-3.1-flash-lite-image",
        "baseline",
        "tight_crop",
        1,
        "0.06",
    ),
    _method(
        "lite_garment_first",
        "google/gemini-3.1-flash-lite-image",
        "baseline",
        "garment_first",
        1,
        "0.06",
    ),
    _method(
        "lite_duplicate_garment",
        "google/gemini-3.1-flash-lite-image",
        "baseline",
        "duplicate_garment",
        1,
        "0.06",
    ),
    _method(
        "lite_background_removed",
        "google/gemini-3.1-flash-lite-image",
        "baseline",
        "background_removed",
        1,
        "0.06",
    ),
    _method(
        "lite_identity_tight_crop",
        "google/gemini-3.1-flash-lite-image",
        "identity_negative",
        "tight_crop",
        1,
        "0.06",
    ),
    _method(
        "lite_identity_detail_board",
        "google/gemini-3.1-flash-lite-image",
        "identity_negative",
        "detail_board",
        1,
        "0.06",
    ),
)

METHOD_SETS = {
    "broad": SEARCH_METHODS,
    "targeted": TARGETED_METHODS,
}

IDENTITY_PRIORITY_SUFFIX = """
PRODUCT-IDENTITY PRIORITY:
The garment must remain the exact referenced product, not merely the same category.
Prioritize readable branding, exact panel and pocket geometry, closures, seams, sole/toe shape,
material boundaries, texture, and color over creative styling. Do not simplify, redesign,
substitute, mirror, move, add, or remove product-defining details. Keep the person and setting
natural, but sacrifice aesthetic embellishment before sacrificing garment fidelity.
""".strip()

NEGATIVE_CONSTRAINT_SUFFIX = """
NEGATIVE CONSTRAINTS:
Do not remove, blur, replace, misspell, or invent visible branding or text.
Do not change the number, position, orientation, or geometry of pockets, panels, seams,
zippers, buttons, closures, eyelets, laces, soles, collars, cuffs, or waist details.
Do not change the source color family, material boundaries, surface texture, garment length,
or silhouette. Do not mirror asymmetric details. Do not add details hidden by the packshot.
""".strip()

REPAIR_PROMPT = """Edit reference 1 rather than creating a new composition.
Keep the person's identity, face, body, pose, framing, lighting, camera, and background unchanged.
Use the remaining garment packshot reference(s) as the sole product truth. Correct only the worn
garment so it matches the exact source product: branding/text, color, silhouette, length, panels,
pockets, seams, closures, zippers, buttons, sole/toe geometry, material boundaries, and texture.
Do not add accessories, alter the person, restyle the scene, or invent hidden details."""

_DEFAULT_REFERENCE_ORDER = """using the supplied references in this order:
1. the person/model image,
2. the environment image,
3. the garment packshot image(s)."""

_GARMENT_FIRST_REFERENCE_ORDER = """using the supplied references in this order:
1. the garment packshot image,
2. the person/model image,
3. the environment image."""

_DUPLICATE_REFERENCE_NOTE = """
References 3 and 4 are duplicate views of the same garment. Treat both as product evidence,
not as two garments. Dress the person in one instance of the garment.
""".strip()


def method_prompt(method: SearchMethod, baseline_prompt: str) -> str:
    """Return the predeclared prompt for a method."""

    prompt = baseline_prompt
    if method.reference_mode == "garment_first":
        prompt = prompt.replace(_DEFAULT_REFERENCE_ORDER, _GARMENT_FIRST_REFERENCE_ORDER)
    if method.reference_mode == "duplicate_garment":
        prompt = f"{prompt.rstrip()}\n\n{_DUPLICATE_REFERENCE_NOTE}\n"

    if method.prompt_kind == "baseline":
        return prompt
    if method.prompt_kind == "identity":
        return f"{prompt.rstrip()}\n\n{IDENTITY_PRIORITY_SUFFIX}\n"
    if method.prompt_kind == "identity_negative":
        return (
            f"{prompt.rstrip()}\n\n{IDENTITY_PRIORITY_SUFFIX}\n\n"
            f"{NEGATIVE_CONSTRAINT_SUFFIX}\n"
        )
    raise ValueError(f"unsupported prompt kind: {method.prompt_kind}")


def _rgb(path: Path) -> Image.Image:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
    background = Image.new("RGBA", image.size, "white")
    background.alpha_composite(image)
    return background.convert("RGB")


def _background_color(image: Image.Image) -> tuple[int, int, int]:
    corners = (
        image.getpixel((0, 0)),
        image.getpixel((image.width - 1, 0)),
        image.getpixel((0, image.height - 1)),
        image.getpixel((image.width - 1, image.height - 1)),
    )
    average = tuple(
        round(sum(pixel[channel] for pixel in corners) / len(corners))
        for channel in range(3)
    )
    return cast(tuple[int, int, int], average)


def _foreground_mask(image: Image.Image, threshold: int = 42) -> Image.Image:
    background = _background_color(image)
    threshold_squared = threshold * threshold
    mask = Image.new("L", image.size)
    values = []
    for red, green, blue in image.getdata():
        distance = (
            (red - background[0]) ** 2
            + (green - background[1]) ** 2
            + (blue - background[2]) ** 2
        )
        values.append(255 if distance > threshold_squared else 0)
    mask.putdata(values)
    return mask


def create_tight_crop(garment_path: Path, output_path: Path) -> Path:
    """Crop deterministic corner-background whitespace around a garment."""

    image = _rgb(garment_path)
    bbox = _foreground_mask(image).getbbox()
    if bbox is None:
        crop = image
    else:
        left, top, right, bottom = bbox
        padding = round(max(right - left, bottom - top) * 0.06)
        crop = image.crop(
            (
                max(0, left - padding),
                max(0, top - padding),
                min(image.width, right + padding),
                min(image.height, bottom + padding),
            )
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(output_path, format="JPEG", quality=92, optimize=True)
    return output_path


def create_background_removed(garment_path: Path, output_path: Path) -> Path:
    """Replace the corner-like background with white."""

    image = _rgb(garment_path)
    mask = _foreground_mask(image)
    cleaned = Image.new("RGB", image.size, "white")
    cleaned.paste(image, mask=mask)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.save(output_path, format="JPEG", quality=92, optimize=True)
    return output_path


def _crop(image: Image.Image, top: float, bottom: float) -> Image.Image:
    height = image.height
    return image.crop((0, round(top * height), image.width, round(bottom * height)))


def _panel(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    contained = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
    panel = Image.new("RGB", size, "white")
    offset = ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2)
    panel.paste(contained, offset)
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


def method_reference_paths(
    case: Case,
    method: SearchMethod,
    work_dir: Path,
) -> tuple[Path, ...]:
    """Return ordered references for one predeclared method."""

    if method.reference_mode == "direct":
        return case.reference_paths
    if method.reference_mode == "detail_board":
        board = create_detail_board(case.garments[0], work_dir / "garment-detail-board.jpg")
        return (case.model, case.environment, board)
    if method.reference_mode == "tight_crop":
        crop = create_tight_crop(case.garments[0], work_dir / "garment-tight-crop.jpg")
        return (case.model, case.environment, crop)
    if method.reference_mode == "garment_first":
        return (*case.garments, case.model, case.environment)
    if method.reference_mode == "duplicate_garment":
        return (case.model, case.environment, *case.garments, *case.garments)
    if method.reference_mode == "background_removed":
        cleaned = create_background_removed(
            case.garments[0],
            work_dir / "garment-background-removed.jpg",
        )
        return (case.model, case.environment, cleaned)
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
