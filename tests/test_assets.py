import json
from pathlib import Path

import pytest

from weon_eval.assets import AssetError, prepare_case_inputs
from weon_eval.cases import Case

PNG = b"\x89PNG\r\n\x1a\nmock-png"
JPEG = b"\xff\xd8\xffmock-jpeg"


def _case(tmp_path: Path) -> Case:
    return Case(
        id="D01",
        split="development",
        model=tmp_path / "inputs/models/person.png",
        environment=tmp_path / "inputs/environments/street.png",
        garments=(tmp_path / "inputs/garments/shorts.png",),
    )


def _write_sources(path: Path, sources: dict[Path, str]) -> None:
    payload = {"assets": {str(key): value for key, value in sources.items()}}
    path.write_text(json.dumps(payload))


def test_prepare_case_inputs_downloads_only_selected_references_in_order(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)
    sources_path = tmp_path / "asset_sources.json"
    sources = {
        case.model: "https://example.test/person.png",
        case.environment: "https://example.test/street.png",
        case.garments[0]: "https://example.test/shorts.png",
        tmp_path / "inputs/models/unused.png": "https://example.test/unused.png",
    }
    _write_sources(sources_path, sources)
    calls: list[str] = []
    payloads = {
        sources[case.model]: PNG,
        sources[case.environment]: PNG,
        sources[case.garments[0]]: PNG,
    }

    def downloader(url: str) -> bytes:
        calls.append(url)
        return payloads[url]

    prepared = prepare_case_inputs(case, sources_path, downloader=downloader)

    assert prepared == case.reference_paths
    assert calls == [
        sources[case.model],
        sources[case.environment],
        sources[case.garments[0]],
    ]
    assert case.model.read_bytes() == PNG
    assert case.environment.read_bytes() == PNG
    assert case.garments[0].read_bytes() == PNG


def test_prepare_case_inputs_rejects_missing_source_mapping(tmp_path: Path) -> None:
    case = _case(tmp_path)
    sources_path = tmp_path / "asset_sources.json"
    _write_sources(
        sources_path,
        {
            case.model: "https://example.test/person.png",
            case.environment: "https://example.test/street.png",
        },
    )

    with pytest.raises(AssetError, match="no source configured for"):
        prepare_case_inputs(case, sources_path, downloader=lambda _url: PNG)


def test_prepare_case_inputs_rejects_mismatched_image_extension(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)
    jpg_garment = tmp_path / "inputs/garments/shorts.jpg"
    case = Case(
        id=case.id,
        split=case.split,
        model=case.model,
        environment=case.environment,
        garments=(jpg_garment,),
    )
    sources_path = tmp_path / "asset_sources.json"
    _write_sources(
        sources_path,
        {
            case.model: "https://example.test/person.png",
            case.environment: "https://example.test/street.png",
            jpg_garment: "https://example.test/shorts.jpg",
        },
    )

    with pytest.raises(AssetError, match="does not match .+shorts.jpg"):
        prepare_case_inputs(case, sources_path, downloader=lambda _url: PNG)
