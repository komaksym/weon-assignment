from pathlib import Path

from PIL import Image

from weon_eval.cases import Case
from weon_eval.search_methods import (
    SEARCH_METHODS,
    create_detail_board,
    method_prompt,
    method_reference_paths,
)


def test_search_method_order_is_frozen() -> None:
    assert [method.name for method in SEARCH_METHODS] == [
        "lite_direct",
        "lite_identity_prompt",
        "lite_detail_board",
        "lite_two_pass_repair",
        "nano25_direct",
        "nano31_direct",
        "nano31_detail_board",
        "seedream_direct",
        "seedream_detail_board",
        "gpt_image_1_mini_direct",
        "gpt_image_1_mini_detail_board",
        "gpt_image_2_direct",
        "gpt_image_2_detail_board",
        "nano31_two_pass_repair",
    ]


def test_detail_board_is_deterministic_and_replaces_only_garment(tmp_path: Path) -> None:
    model = tmp_path / "model.png"
    environment = tmp_path / "environment.png"
    garment = tmp_path / "garment.png"
    for path, color in ((model, "blue"), (environment, "green"), (garment, "olive")):
        Image.new("RGB", (80, 120), color).save(path)
    case = Case("D01", "development", model, environment, (garment,))
    method = next(item for item in SEARCH_METHODS if item.name == "lite_detail_board")

    first = method_reference_paths(case, method, tmp_path / "run-a")
    second_board = create_detail_board(garment, tmp_path / "run-b" / "garment-detail-board.jpg")

    assert first[:2] == (model, environment)
    assert first[2].read_bytes() == second_board.read_bytes()
    with Image.open(first[2]) as board:
        assert board.size == (1024, 1024)


def test_identity_prompt_adds_fixed_constraints() -> None:
    method = next(item for item in SEARCH_METHODS if item.name == "lite_identity_prompt")

    prompt = method_prompt(method, "Create a scene.\n")

    assert prompt.startswith("Create a scene.")
    assert "PRODUCT-IDENTITY PRIORITY" in prompt
    assert "Do not simplify, redesign" in prompt
