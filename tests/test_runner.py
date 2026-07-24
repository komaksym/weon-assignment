import base64
import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from weon_eval.cases import Case
from weon_eval.openrouter import GenerationResult
from weon_eval.runner import build_payload, prepare_reference, prepare_references, run_case


def _write_image(path: Path, size: tuple[int, int]) -> None:
    Image.new("RGB", size, 127).save(path)


def _jpeg_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (8, 8), "red").save(output, format="JPEG")
    return output.getvalue()


def _case(tmp_path: Path) -> Case:
    refs = []
    for name, size in (
        ("model.png", (2048, 1024)),
        ("environment.png", (800, 600)),
        ("garment.png", (1024, 2048)),
    ):
        path = tmp_path / name
        _write_image(path, size)
        refs.append(path)
    return Case(
        id="D01",
        split="development",
        model=refs[0],
        environment=refs[1],
        garments=(refs[2],),
    )


def test_build_payload_compacts_references_and_keeps_order(tmp_path: Path) -> None:
    case = _case(tmp_path)
    prepared = prepare_references(case)

    payload = build_payload(case, "prompt", "google/gemini-3.1-flash-lite-image", prepared)

    encoded = [item["image_url"]["url"] for item in payload["input_references"]]
    assert all(url.startswith("data:image/jpeg;base64,") for url in encoded)
    assert [reference.path for reference in prepared] == list(case.reference_paths)
    assert prepared[0].original_dimensions == (2048, 1024)
    assert prepared[0].prepared_dimensions == (1024, 512)
    assert prepared[2].prepared_dimensions == (512, 1024)
    assert payload["aspect_ratio"] == "3:4"
    assert payload["resolution"] == "1K"
    assert payload["n"] == 1


def test_prepare_reference_composites_palette_transparency_onto_white(
    tmp_path: Path,
) -> None:
    path = tmp_path / "palette.png"
    image = Image.new("P", (20, 10))
    image.putpalette([255, 0, 0, 0, 0, 255] + [0, 0, 0] * 254)
    for x in range(10, 20):
        for y in range(10):
            image.putpixel((x, y), 1)
    image.save(path, transparency=0)

    prepared = prepare_reference(path)
    encoded = prepared.data_url.split(",", 1)[1]
    with Image.open(BytesIO(base64.b64decode(encoded))) as output:
        output.load()
        transparent_pixel = output.getpixel((2, 5))
        opaque_pixel = output.getpixel((17, 5))

    assert all(channel >= 240 for channel in transparent_pixel)
    assert opaque_pixel[2] >= 150
    assert opaque_pixel[0] <= 100
    assert opaque_pixel[1] <= 100


def test_run_case_saves_media_specific_image_and_reference_metadata(tmp_path: Path) -> None:
    case = _case(tmp_path)
    generated = _jpeg_bytes()

    def generator(payload: dict[str, object], api_key: str) -> GenerationResult:
        assert api_key == "secret"
        assert payload["prompt"] == "prompt"
        return GenerationResult(
            image=generated,
            cost_usd=Decimal("0.03487875"),
            media_type="image/jpeg",
        )

    result_dir = run_case(
        case=case,
        prompt="prompt",
        model="google/gemini-3.1-flash-lite-image",
        strategy="baseline",
        api_key="secret",
        output_root=tmp_path / "outputs",
        generator=generator,
        clock=iter((10.0, 16.264)).__next__,
    )

    assert (result_dir / "image.jpg").read_bytes() == generated
    metadata = json.loads((result_dir / "metadata.json").read_text())
    assert metadata["aspect_ratio"] == "3:4"
    assert metadata["case_id"] == "D01"
    assert metadata["cost_usd"] == "0.03487875"
    assert metadata["image_file"] == "image.jpg"
    assert metadata["latency_seconds"] == pytest.approx(6.264)
    assert metadata["model"] == "google/gemini-3.1-flash-lite-image"
    assert metadata["output_media_type"] == "image/jpeg"
    assert metadata["resolution"] == "1K"
    assert metadata["strategy"] == "baseline"
    assert [item["path"] for item in metadata["references"]] == [
        str(path) for path in case.reference_paths
    ]
    assert metadata["references"][0]["original_dimensions"] == [2048, 1024]
    assert metadata["references"][0]["prepared_dimensions"] == [1024, 512]
    assert metadata["references"][0]["prepared_media_type"] == "image/jpeg"
    assert metadata["references"][0]["prepared_bytes"] > 0
