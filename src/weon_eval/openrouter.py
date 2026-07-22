"""Minimal OpenRouter Images API boundary."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import httpx

IMAGES_URL = "https://openrouter.ai/api/v1/images"


class GenerationError(RuntimeError):
    """Raised when OpenRouter does not return one usable image."""


@dataclass(frozen=True)
class GenerationResult:
    """Generated image bytes and API-reported cost."""

    image: bytes
    cost_usd: Decimal | None


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
        encoded = body["data"][0]["b64_json"]
        image = base64.b64decode(encoded, validate=True)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise GenerationError("OpenRouter returned no usable image") from exc

    return GenerationResult(image=image, cost_usd=_reported_cost(body))
