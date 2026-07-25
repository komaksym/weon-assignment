from pathlib import Path

from PIL import Image, ImageDraw

from weon_eval.cases import Case
from weon_eval.search_methods import (
    TARGETED_METHODS,
    create_background_removed,
    create_tight_crop,
    method_prompt,
    method_reference_paths,
)


def _case(tmp_path: Path) -> Case:
    model = tmp_path / "model.png"
    environment = tmp_path / "environment.png"
    garment = tmp_path / "garment.png"
    Image.new("RGB", (64, 96), "blue").save(model)
    Image.new("RGB", (96, 64), "green").save(environment)
    image = Image.new("RGB", (160, 200), "white")
    ImageDraw.Draw(image).rectangle((45, 30, 115, 175), fill="olive")
    image.save(garment)
    return Case("D01", "development", model, environment, (garment,))


def _method(name: str):
    return next(item for item in TARGETED_METHODS if item.name == name)


def test_targeted_method_order_is_frozen() -> None:
    assert [method.name for method in TARGETED_METHODS] == [
        "lite_identity_negative",
        "lite_tight_crop",
        "lite_garment_first",
        "lite_duplicate_garment",
        "lite_background_removed",
        "lite_identity_tight_crop",
        "lite_identity_detail_board",
    ]


def test_identity_negative_prompt_keeps_fixed_constraints() -> None:
    prompt = method_prompt(_method("lite_identity_negative"), "Create a scene.\n")

    assert "PRODUCT-IDENTITY PRIORITY" in prompt
    assert "NEGATIVE CONSTRAINTS" in prompt
    assert "Do not remove, blur, replace, misspell" in prompt
    assert "Do not mirror asymmetric details" in prompt


def test_garment_first_prompt_and_reference_order_match(tmp_path: Path) -> None:
    case = _case(tmp_path)
    method = _method("lite_garment_first")
    baseline = """Create using the supplied references in this order:
1. the person/model image,
2. the environment image,
3. the garment packshot image(s).
"""

    prompt = method_prompt(method, baseline)
    paths = method_reference_paths(case, method, tmp_path / "work")

    assert "1. the garment packshot image" in prompt
    assert paths == (case.garments[0], case.model, case.environment)


def test_duplicate_garment_is_one_product_with_two_evidence_slots(tmp_path: Path) -> None:
    case = _case(tmp_path)
    method = _method("lite_duplicate_garment")

    prompt = method_prompt(method, "Create a scene.\n")
    paths = method_reference_paths(case, method, tmp_path / "work")

    assert paths == (case.model, case.environment, case.garments[0], case.garments[0])
    assert "duplicate views of the same garment" in prompt
    assert "one instance of the garment" in prompt


def test_tight_crop_is_deterministic_and_removes_whitespace(tmp_path: Path) -> None:
    case = _case(tmp_path)

    first = create_tight_crop(case.garments[0], tmp_path / "a.jpg")
    second = create_tight_crop(case.garments[0], tmp_path / "b.jpg")

    assert first.read_bytes() == second.read_bytes()
    with Image.open(first) as crop:
        assert crop.width < 160
        assert crop.height < 200


def test_background_removal_is_deterministic_and_preserves_subject(tmp_path: Path) -> None:
    case = _case(tmp_path)

    first = create_background_removed(case.garments[0], tmp_path / "a.jpg")
    second = create_background_removed(case.garments[0], tmp_path / "b.jpg")

    assert first.read_bytes() == second.read_bytes()
    with Image.open(first) as cleaned:
        assert cleaned.getpixel((0, 0))[0] > 245
        center = cleaned.getpixel((80, 100))
        assert center[1] > center[0]
