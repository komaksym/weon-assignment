import json
from decimal import Decimal
from pathlib import Path

from weon_eval.cases import Case
from weon_eval.openrouter import GenerationResult
from weon_eval.runner import build_payload, run_case


def test_build_payload_keeps_model_environment_garment_order(tmp_path: Path) -> None:
    refs = []
    for name in ("model.png", "environment.png", "garment.png"):
        path = tmp_path / name
        path.write_bytes(name.encode())
        refs.append(path)
    case = Case(
        id="D01",
        split="development",
        model=refs[0],
        environment=refs[1],
        garments=(refs[2],),
    )

    payload = build_payload(case, "prompt", "image-model")

    encoded = [item["image_url"]["url"] for item in payload["input_references"]]
    assert encoded[0].endswith("bW9kZWwucG5n")
    assert encoded[1].endswith("ZW52aXJvbm1lbnQucG5n")
    assert encoded[2].endswith("Z2FybWVudC5wbmc=")
    assert payload["aspect_ratio"] == "3:4"
    assert payload["resolution"] == "2K"
    assert payload["n"] == 1


def test_run_case_saves_image_and_small_metadata(tmp_path: Path) -> None:
    refs = []
    for name in ("model.png", "environment.png", "garment.png"):
        path = tmp_path / name
        path.write_bytes(b"png")
        refs.append(path)
    case = Case(
        id="D01",
        split="development",
        model=refs[0],
        environment=refs[1],
        garments=(refs[2],),
    )

    def generator(payload: dict[str, object], api_key: str) -> GenerationResult:
        assert api_key == "secret"
        assert payload["prompt"] == "prompt"
        return GenerationResult(image=b"generated", cost_usd=Decimal("0.04"))

    result_dir = run_case(
        case=case,
        prompt="prompt",
        model="bytedance-seed/seedream-4.5",
        strategy="baseline",
        api_key="secret",
        output_root=tmp_path / "outputs",
        generator=generator,
    )

    assert (result_dir / "image.png").read_bytes() == b"generated"
    metadata = json.loads((result_dir / "metadata.json").read_text())
    assert metadata == {
        "case_id": "D01",
        "cost_usd": "0.04",
        "model": "bytedance-seed/seedream-4.5",
        "prompt": "prompt",
        "references": [str(path) for path in refs],
        "strategy": "baseline",
    }
