import base64
from decimal import Decimal

import httpx
import pytest

from weon_eval.openrouter import GenerationError, generate_image


def test_generate_image_returns_bytes_media_type_and_reported_cost() -> None:
    image = b"\xff\xd8\xfffake-jpeg"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://openrouter.ai/api/v1/images"
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "b64_json": base64.b64encode(image).decode(),
                        "media_type": "image/jpeg",
                    }
                ],
                "usage": {"cost": 0.03487875},
            },
        )

    result = generate_image(
        payload={"model": "model", "prompt": "prompt"},
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )

    assert result.image == image
    assert result.media_type == "image/jpeg"
    assert result.cost_usd == Decimal("0.03487875")


def test_generate_image_infers_media_type_when_response_omits_it() -> None:
    image = b"\x89PNG\r\n\x1a\nfake-png"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(image).decode()}]},
        )

    result = generate_image(
        payload={"model": "model", "prompt": "prompt"},
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )

    assert result.media_type == "image/png"


def test_generate_image_surfaces_safe_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "unsupported reference count"}})

    with pytest.raises(GenerationError, match="unsupported reference count"):
        generate_image(
            payload={"model": "model", "prompt": "prompt"},
            api_key="secret",
            transport=httpx.MockTransport(handler),
        )
