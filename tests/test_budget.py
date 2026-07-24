from decimal import Decimal

import httpx
import pytest

from weon_eval.budget import BudgetError, KeyAllowance, can_spend, get_key_allowance


def test_get_key_allowance_uses_limit_remaining() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"data": {"limit": 20, "usage": 3, "limit_remaining": 17.25}},
        )
    )

    allowance = get_key_allowance("secret", transport=transport)

    assert allowance == KeyAllowance(
        remaining_usd=Decimal("17.25"),
        limit_usd=Decimal("20"),
        usage_usd=Decimal("3"),
    )


def test_get_key_allowance_falls_back_to_limit_minus_usage() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"data": {"limit": 20, "usage": 7.5}})
    )

    allowance = get_key_allowance("secret", transport=transport)

    assert allowance.remaining_usd == Decimal("12.5")


def test_get_key_allowance_rejects_unbounded_key() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"data": {"usage": 7.5}})
    )

    with pytest.raises(BudgetError, match="no finite remaining allowance"):
        get_key_allowance("secret", transport=transport)


def test_can_spend_preserves_floor() -> None:
    allowance = KeyAllowance(Decimal("10.08"), Decimal("20"), Decimal("9.92"))

    assert can_spend(allowance, Decimal("0.08"))
    assert not can_spend(allowance, Decimal("0.081"))
