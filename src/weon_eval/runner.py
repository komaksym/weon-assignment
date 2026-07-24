"""Build and persist one garment-consistency experiment run."""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from time import monotonic

from PIL import Image, ImageOps

from weon_eval.cases import Case
from weon_eval.openrouter import GenerationResult, generate_image

Generator = Callable[[dict[str, object], str], GenerationResult]
REFERENCE_MAX_PX = 1024
REFERENCE_JPEG_QUALITY = 85
OUTPUT_ASPECT_RATIO = "3:4"
OUTPUT_RESOLUTION = "1K"


@dataclass(frozen=True)
class PreparedReference:
    """One compact reference and the dimensions needed for run metadata."""

    path: Path
    data_url: str
    original_dimensions: tuple[int, int]
    prepared_dimensions: tuple[int, int]
    prepared_bytes: int

    def metadata(self) -> dict[str, object]:
        """Return a JSON-serializable reference record."""

        return {
            "path": str(self.path),
            "original_dimensions": list(self.original_dimensions),
            "prepared_dimensions": list(self.prepared_dimensions),
            "prepared_bytes": self.prepared_bytes,
            "prepared_media_type": "image/jpeg",
        }


def _to_rgb(image: Image.Image) -> Image.Image:
    if image.mode == "RGB":
        return image
    background = Image.new("RGB", image.size, "white")
    if "A" in image.getbands():
        background.paste(image, mask=image.getchannel("A"))
    else:
        background.paste(image)
    return background


def prepare_reference(
    path: Path,
    *,
    max_px: int = REFERENCE_MAX_PX,
    quality: int = REFERENCE_JPEG_QUALITY,
) -> PreparedReference:
    """Resize one input in memory and encode it as a compact JPEG data URL."""

    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).copy()
    original_dimensions = image.size
    image.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)
    image = _to_rgb(image)

    output = BytesIO()
    image.save(output, format="JPEG", quality=quality, optimize=True)
    prepared = output.getvalue()
    encoded = base64.b64encode(prepared).decode("ascii")
    return PreparedReference(
        path=path,
        data_url=f"data:image/jpeg;base64,{encoded}",
        original_dimensions=original_dimensions,
        prepared_dimensions=image.size,
        prepared_bytes=len(prepared),
    )


def prepare_references(case: Case) -> tuple[PreparedReference, ...]:
    """Prepare case references in model, environment, garment order."""

    return tuple(prepare_reference(path) for path in case.reference_paths)


def build_payload(
    case: Case,
    prompt: str,
    model: str,
    prepared_references: tuple[PreparedReference, ...] | None = None,
) -> dict[str, object]:
    """Build one unified Images API request."""

    references = prepared_references or prepare_references(case)
    if tuple(reference.path for reference in references) != case.reference_paths:
        raise ValueError("prepared references do not match case order")
    return {
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


def _extension(media_type: str) -> str:
    extensions = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    try:
        return extensions[media_type]
    except KeyError as exc:
        raise ValueError(f"unsupported generated media type: {media_type}") from exc


def run_case(
    *,
    case: Case,
    prompt: str,
    model: str,
    strategy: str,
    api_key: str,
    output_root: Path,
    generator: Generator = generate_image,
    clock: Callable[[], float] = monotonic,
) -> Path:
    """Generate one image and save it with compact metadata."""

    result_dir = output_root / case.id / model.replace("/", "_") / strategy
    if result_dir.exists():
        raise FileExistsError(f"output already exists: {result_dir}")

    prepared_references = prepare_references(case)
    payload = build_payload(case, prompt, model, prepared_references)
    started_at = clock()
    result = generator(payload, api_key)
    latency_seconds = clock() - started_at
    result_dir.mkdir(parents=True)
    image_path = result_dir / f"image{_extension(result.media_type)}"
    image_path.write_bytes(result.image)
    metadata = {
        "aspect_ratio": OUTPUT_ASPECT_RATIO,
        "case_id": case.id,
        "cost_usd": str(result.cost_usd) if result.cost_usd is not None else None,
        "image_file": image_path.name,
        "latency_seconds": latency_seconds,
        "model": model,
        "output_media_type": result.media_type,
        "prompt": prompt,
        "references": [reference.metadata() for reference in prepared_references],
        "resolution": OUTPUT_RESOLUTION,
        "strategy": strategy,
    }
    (result_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return result_dir
