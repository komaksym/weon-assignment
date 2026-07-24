"""OpenRouter key allowance checks for paid experiment guards."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import httpx

KEY_URL = "https://openrouter.ai/api/v1/key"


class BudgetError(RuntimeError):
    """Raised when the remaining key allowance cannot be determined safely."""


@dataclass(frozen=True)
class KeyAllowance:
    """Current key usage and remaining USD allowance."""

    remaining_usd: Decimal
    limit_usd: Decimal | None
    usage_usd: Decimal | None


def _decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise BudgetError(f"OpenRouter key response has no numeric {field}")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BudgetError(f"OpenRouter key response has invalid {field}") from exc


def _error_message(response: httpx.Response) -> str:
    try:
        payload: object = response.json()
    except ValueError:
        return f"OpenRouter returned HTTP {response.status_code}"
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return str(error["message"])
    return f"OpenRouter returned HTTP {response.status_code}"


def get_key_allowance(
    api_key: str,
    *,
    transport: httpx.BaseTransport | None = None,
) -> KeyAllowance:
    """Read key-specific remaining allowance without retries."""

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with httpx.Client(transport=transport, timeout=30) as client:
            response = client.get(KEY_URL, headers=headers)
    except httpx.HTTPError as exc:
        raise BudgetError(f"OpenRouter key request failed: {exc}") from exc
    if response.is_error:
        raise BudgetError(_error_message(response))

    try:
        payload: object = response.json()
    except ValueError as exc:
        raise BudgetError("OpenRouter returned invalid key JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise BudgetError("OpenRouter returned no key data")
    data = payload["data"]

    raw_remaining = data.get("limit_remaining")
    raw_limit = data.get("limit")
    raw_usage = data.get("usage")
    limit_usd = _decimal(raw_limit, "limit") if raw_limit is not None else None
    usage_usd = _decimal(raw_usage, "usage") if raw_usage is not None else None
    if raw_remaining is not None:
        remaining = _decimal(raw_remaining, "limit_remaining")
    elif limit_usd is not None and usage_usd is not None:
        remaining = limit_usd - usage_usd
    else:
        raise BudgetError("OpenRouter key has no finite remaining allowance")
    if remaining < 0:
        raise BudgetError("OpenRouter key remaining allowance is negative")
    return KeyAllowance(
        remaining_usd=remaining,
        limit_usd=limit_usd,
        usage_usd=usage_usd,
    )


def can_spend(
    allowance: KeyAllowance,
    reserve_usd: Decimal,
    floor_usd: Decimal = Decimal("10.00"),
) -> bool:
    """Return whether one request reserve can be spent without crossing the floor."""

    if reserve_usd < 0 or floor_usd < 0:
        raise ValueError("reserve and floor must be non-negative")
    return allowance.remaining_usd - reserve_usd >= floor_usd
