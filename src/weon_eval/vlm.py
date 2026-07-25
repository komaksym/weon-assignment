"""Small OpenRouter vision boundary for structured experiment judgments."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import monotonic

import httpx

from weon_eval.runner import prepare_reference

CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
Clock = Callable[[], float]


class VlmError(RuntimeError):
    """Raised when the evaluator cannot return one valid JSON object."""


@dataclass(frozen=True)
class JsonResult:
    """Structured VLM output and request measurements."""

    data: dict[str, object]
    cost_usd: Decimal | None
    latency_seconds: float


def _error_message(response: httpx.Response) -> str:
    try:
        payload: object = response.json()
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
        raise VlmError("OpenRouter returned an invalid evaluator cost") from exc


def _content(payload: object) -> str:
    if not isinstance(payload, dict):
        raise VlmError("OpenRouter returned no evaluator response")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise VlmError("OpenRouter returned no evaluator response")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise VlmError("OpenRouter returned no evaluator response")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise VlmError("OpenRouter returned no evaluator response")
    content = message.get("content")
    if not isinstance(content, str):
        raise VlmError("OpenRouter returned no evaluator response")
    return content


def request_json(
    *,
    model: str,
    prompt: str,
    image_paths: Sequence[Path],
    schema_name: str,
    schema: Mapping[str, object],
    api_key: str,
    transport: httpx.BaseTransport | None = None,
    clock: Clock = monotonic,
) -> JsonResult:
    """Send one vision request with strict JSON-schema output and no retry."""

    content: list[dict[str, object]] = [{"type": "text", "text": prompt}]
    content.extend(
        {
            "type": "image_url",
            "image_url": {"url": prepare_reference(path).data_url},
        }
        for path in image_paths
    )
    payload: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "provider": {"require_parameters": True},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": dict(schema),
            },
        },
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    started_at = clock()
    try:
        with httpx.Client(transport=transport, timeout=180) as client:
            response = client.post(CHAT_COMPLETIONS_URL, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise VlmError(f"OpenRouter evaluator request failed: {exc}") from exc
    latency_seconds = clock() - started_at
    if response.is_error:
        raise VlmError(_error_message(response))

    try:
        body: object = response.json()
        parsed: object = json.loads(_content(body))
    except (ValueError, json.JSONDecodeError) as exc:
        raise VlmError("OpenRouter returned invalid evaluator JSON") from exc
    if not isinstance(parsed, dict):
        raise VlmError("OpenRouter evaluator JSON must be an object")
    return JsonResult(
        data=parsed,
        cost_usd=_reported_cost(body),
        latency_seconds=latency_seconds,
    )
