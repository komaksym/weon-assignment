import json
from decimal import Decimal
from pathlib import Path

import httpx
from PIL import Image

from weon_eval.vlm import CHAT_COMPLETIONS_URL, request_json


def test_request_json_sends_images_and_parses_structured_output(tmp_path: Path) -> None:
    image_path = tmp_path / "garment.png"
    Image.new("RGB", (12, 8), "olive").save(image_path)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == CHAT_COMPLETIONS_URL
        payload = json.loads(request.content)
        assert payload["model"] == "google/gemini-2.5-flash-lite"
        assert payload["response_format"]["type"] == "json_schema"
        content = payload["messages"][0]["content"]
        assert content[0] == {"type": "text", "text": "inspect"}
        assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"attributes":{"color":"olive"}}'}}
                ],
                "usage": {"cost": 0.0001},
            },
        )

    result = request_json(
        model="google/gemini-2.5-flash-lite",
        prompt="inspect",
        image_paths=(image_path,),
        schema_name="attributes",
        schema={"type": "object"},
        api_key="secret",
        transport=httpx.MockTransport(handler),
        clock=iter((10.0, 10.25)).__next__,
    )

    assert result.data == {"attributes": {"color": "olive"}}
    assert result.cost_usd == Decimal("0.0001")
    assert result.latency_seconds == 0.25
