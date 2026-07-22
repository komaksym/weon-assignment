import base64
from decimal import Decimal

import httpx
import pytest

from weon_eval.openrouter import GenerationError, generate_image


def test_generate_image_returns_bytes_and_reported_cost() -> None:
    image = b"fake-png"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://openrouter.ai/api/v1/images"
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(
            200,
            json={
                "data": [{"b64_json": base64.b64encode(image).decode()}],
                "usage": {"cost": 0.04},
            },
        )

    result = generate_image(
        payload={"model": "model", "prompt": "prompt"},
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )

    assert result.image == image
    assert result.cost_usd == Decimal("0.04")


def test_generate_image_surfaces_safe_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "unsupported reference count"}})

    with pytest.raises(GenerationError, match="unsupported reference count"):
        generate_image(
            payload={"model": "model", "prompt": "prompt"},
            api_key="secret",
            transport=httpx.MockTransport(handler),
        )
