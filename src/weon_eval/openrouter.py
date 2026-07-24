"""Minimal OpenRouter Images API boundary."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO

import httpx
from PIL import Image

IMAGES_URL = "https://openrouter.ai/api/v1/images"
_IMAGE_MEDIA_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class GenerationError(RuntimeError):
    """Raised when OpenRouter does not return one usable image."""


@dataclass(frozen=True)
class GenerationResult:
    """Generated image bytes, media type, and API-reported cost."""

    image: bytes
    cost_usd: Decimal | None
    media_type: str = "image/png"


def _error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"OpenRouter returned HTTP {response.status_code}"

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message
    return f"OpenRouter returned HTTP {response.status_code}"


def _reported_cost(payload: object) -> Decimal | None:
    if not isinstance(payload, dict):
        return None
    usage = payload.get("usage")
    if not isinstance(usage, dict) or usage.get("cost") is None:
        return None
    try:
        return Decimal(str(usage["cost"]))
    except InvalidOperation as exc:
        raise GenerationError("OpenRouter returned an invalid cost") from exc


def _validated_media_type(image: bytes) -> str:
    try:
        with Image.open(BytesIO(image)) as generated:
            image_format = generated.format
            generated.verify()
        with Image.open(BytesIO(image)) as generated:
            generated.load()
    except (OSError, ValueError) as exc:
        raise GenerationError("OpenRouter returned invalid image bytes") from exc

    if image_format is None:
        raise GenerationError("OpenRouter returned an unsupported image format")
    try:
        return _IMAGE_MEDIA_TYPES[image_format]
    except KeyError as exc:
        raise GenerationError("OpenRouter returned an unsupported image format") from exc


def generate_image(
    payload: Mapping[str, object],
    api_key: str,
    transport: httpx.BaseTransport | None = None,
) -> GenerationResult:
    """Send one image-generation request without retries."""

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(transport=transport, timeout=180) as client:
            response = client.post(IMAGES_URL, headers=headers, json=dict(payload))
    except httpx.HTTPError as exc:
        raise GenerationError(f"OpenRouter request failed: {exc}") from exc

    if response.is_error:
        raise GenerationError(_error_message(response))

    try:
        body = response.json()
        item = body["data"][0]
        encoded = item["b64_json"]
        image = base64.b64decode(encoded, validate=True)
        raw_media_type = item.get("media_type")
    except (AttributeError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise GenerationError("OpenRouter returned no usable image") from exc

    media_type = _validated_media_type(image)
    if isinstance(raw_media_type, str) and raw_media_type != media_type:
        raise GenerationError("OpenRouter media type does not match generated image")
    return GenerationResult(
        image=image,
        cost_usd=_reported_cost(body),
        media_type=media_type,
    )
