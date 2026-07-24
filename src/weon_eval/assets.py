"""Prepare ignored local reference images from the assignment source manifest."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx

from weon_eval.cases import Case

Downloader = Callable[[str], bytes]


class AssetError(RuntimeError):
    """Raised when an experiment reference cannot be prepared safely."""


def load_asset_sources(path: Path) -> dict[Path, str]:
    """Load local-path-to-source-URL mappings."""

    try:
        payload: object = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise AssetError(f"cannot load asset sources: {exc}") from exc

    raw_assets = payload.get("assets") if isinstance(payload, dict) else None
    if not isinstance(raw_assets, dict):
        raise AssetError("assets must be an object")

    sources: dict[Path, str] = {}
    for raw_path, raw_url in raw_assets.items():
        if not isinstance(raw_path, str) or not raw_path:
            raise AssetError("asset paths must be non-empty strings")
        if not isinstance(raw_url, str) or not raw_url.startswith("https://"):
            raise AssetError(f"invalid source URL for {raw_path}")
        sources[Path(raw_path)] = raw_url
    return sources


def download_asset(url: str) -> bytes:
    """Download one public assignment reference without retries."""

    try:
        response = httpx.get(url, follow_redirects=True, timeout=120)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AssetError(f"cannot download asset: {exc}") from exc
    return response.content


def _image_format(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    raise AssetError("downloaded asset is not a supported PNG or JPEG image")


def _validate_image(path: Path, data: bytes) -> None:
    actual = _image_format(data)
    suffix = path.suffix.lower()
    expected = "png" if suffix == ".png" else "jpeg" if suffix in {".jpg", ".jpeg"} else None
    if expected is None:
        raise AssetError(f"unsupported image extension: {path}")
    if actual != expected:
        raise AssetError(f"downloaded {actual} image does not match {path}")


def prepare_case_inputs(
    case: Case,
    sources_path: Path,
    downloader: Downloader = download_asset,
) -> tuple[Path, ...]:
    """Download and validate only the references required by one case."""

    sources = load_asset_sources(sources_path)
    for path in case.reference_paths:
        source = sources.get(path)
        if source is None:
            raise AssetError(f"no source configured for {path}")
        data = downloader(source)
        _validate_image(path, data)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return case.reference_paths
