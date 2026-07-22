"""Build and persist one garment-consistency experiment run."""

from __future__ import annotations

import base64
import json
import mimetypes
from collections.abc import Callable
from pathlib import Path

from weon_eval.cases import Case
from weon_eval.openrouter import GenerationResult, generate_image

Generator = Callable[[dict[str, object], str], GenerationResult]


def _data_url(path: Path) -> str:
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def build_payload(case: Case, prompt: str, model: str) -> dict[str, object]:
    """Build one dedicated Images API request."""

    references: list[dict[str, object]] = [
        {"type": "image_url", "image_url": {"url": _data_url(path)}}
        for path in case.reference_paths
    ]
    return {
        "model": model,
        "prompt": prompt,
        "input_references": references,
        "n": 1,
        "aspect_ratio": "3:4",
        "resolution": "2K",
    }


def run_case(
    *,
    case: Case,
    prompt: str,
    model: str,
    strategy: str,
    api_key: str,
    output_root: Path,
    generator: Generator = generate_image,
) -> Path:
    """Generate one image and save it with compact metadata."""

    result_dir = output_root / case.id / model.replace("/", "_") / strategy
    if result_dir.exists():
        raise FileExistsError(f"output already exists: {result_dir}")

    result = generator(build_payload(case, prompt, model), api_key)
    result_dir.mkdir(parents=True)
    (result_dir / "image.png").write_bytes(result.image)
    metadata = {
        "case_id": case.id,
        "cost_usd": str(result.cost_usd) if result.cost_usd is not None else None,
        "model": model,
        "prompt": prompt,
        "references": [str(path) for path in case.reference_paths],
        "strategy": strategy,
    }
    (result_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return result_dir
