from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

DEVELOPMENT_SOURCE_BOXES = {
    "D01": (0, 38, 310, 382),
    "D02": (12, 166, 308, 326),
    "D03": (5, 38, 315, 360),
}

HOLDOUT_SOURCE_BOXES = {
    "H01": (15, 198, 405, 415),
    "H02": (5, 35, 415, 492),
}

DEVELOPMENT_CASES = {
    "D01": {
        "title": "Technical shorts",
        "inspect": (
            "double-button waist",
            "zipper placement",
            "pocket geometry",
            "dark reinforcement panels",
            "logo / embroidery",
            "technical-fabric texture",
        ),
        "primary": (0.24, 0.27, 0.76, 0.72),
        "detail": (0.30, 0.32, 0.70, 0.57),
    },
    "D02": {
        "title": "Low-top shoes",
        "inspect": (
            "ARIGATO logo",
            "toe-panel geometry",
            "sole thickness",
            "leather / suede split",
            "perforation",
            "low-top silhouette",
        ),
        "primary": (0.18, 0.69, 0.82, 0.98),
        "detail": (0.24, 0.75, 0.76, 0.94),
    },
    "D03": {
        "title": "Waxed jacket",
        "inspect": (
            "collar shape",
            "front closure",
            "pocket count and placement",
            "seams and panels",
            "jacket length",
            "waxed-material appearance",
        ),
        "primary": (0.20, 0.12, 0.80, 0.74),
        "detail": (0.28, 0.17, 0.72, 0.54),
    },
}

HOLDOUT_CASES = {
    "H01": {
        "title": "Footwear holdout",
        "inspect": DEVELOPMENT_CASES["D02"]["inspect"],
        "primary": (0.18, 0.68, 0.82, 0.98),
        "detail": (0.24, 0.75, 0.76, 0.94),
    },
    "H02": {
        "title": "Shorts holdout",
        "inspect": DEVELOPMENT_CASES["D01"]["inspect"],
        "primary": (0.23, 0.26, 0.77, 0.74),
        "detail": (0.30, 0.31, 0.70, 0.57),
    },
}


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(path, size)


def fit(image: Image.Image, box: tuple[int, int]) -> Image.Image:
    max_width, max_height = box
    scale = min(max_width / image.width, max_height / image.height)
    size = (
        max(1, round(image.width * scale)),
        max(1, round(image.height * scale)),
    )
    return image.resize(size, Image.Resampling.LANCZOS)


def paste_center(
    canvas: Image.Image,
    image: Image.Image,
    box: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    fitted = fit(image, (x1 - x0, y1 - y0))
    x = x0 + (x1 - x0 - fitted.width) // 2
    y = y0 + (y1 - y0 - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    return (x, y, x + fitted.width, y + fitted.height)


def draw_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle(
        box,
        radius=22,
        fill="white",
        outline="#c9ced6",
        width=3,
    )


def crop_normalized(
    image: Image.Image,
    box: tuple[float, float, float, float],
) -> Image.Image:
    x0, y0, x1, y1 = box
    return image.crop(
        (
            round(x0 * image.width),
            round(y0 * image.height),
            round(x1 * image.width),
            round(y1 * image.height),
        )
    )


def clarify(image: Image.Image) -> Image.Image:
    sharpened = image.filter(
        ImageFilter.UnsharpMask(radius=1.5, percent=115, threshold=3)
    )
    sharpened = ImageEnhance.Sharpness(sharpened).enhance(1.15)
    return ImageEnhance.Contrast(sharpened).enhance(1.03)


def load_development_source(root: Path, case_id: str) -> Image.Image:
    with Image.open(root / case_id / "contact_sheet.jpg") as sheet:
        return sheet.crop(DEVELOPMENT_SOURCE_BOXES[case_id]).convert("RGB")


def load_holdout_source(root: Path, case_id: str) -> Image.Image:
    with Image.open(root / case_id / "contact_sheet.jpg") as sheet:
        return sheet.crop(HOLDOUT_SOURCE_BOXES[case_id]).convert("RGB")


def load_development_images(
    root: Path,
    case_id: str,
) -> list[tuple[str, Image.Image]]:
    case_root = root / case_id
    model_root = case_root / "google_gemini-3.1-flash-lite-image"
    paths = (
        ("Baseline", model_root / "baseline" / "image.jpg"),
        ("Structured", model_root / "structured_a" / "image.jpg"),
        ("Best of two", case_root / "best_of_two" / "image.jpg"),
    )
    return [(label, Image.open(path).convert("RGB")) for label, path in paths]


def draw_source_column(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    source: Image.Image,
    box: tuple[int, int, int, int],
    inspection_points: tuple[str, ...],
) -> None:
    draw_panel(draw, box)
    x0, y0, x1, _ = box
    draw.text(
        (x0 + 35, y0 + 35),
        "Source garment",
        font=load_font(44, bold=True),
        fill="#111827",
    )
    paste_center(canvas, source, (x0 + 50, y0 + 120, x1 - 50, y0 + 990))
    draw.text(
        (x0 + 50, y0 + 1040),
        "Ground-truth packshot",
        font=load_font(31, bold=True),
        fill="#111827",
    )
    draw.multiline_text(
        (x0 + 50, y0 + 1095),
        "Use this as the reference.\n"
        "A plausible product is not enough.\n"
        "Exact identity details are what matter.",
        font=load_font(27),
        fill="#4b5563",
        spacing=12,
    )
    draw.text(
        (x0 + 50, y0 + 1280),
        "What to inspect",
        font=load_font(31, bold=True),
        fill="#111827",
    )
    draw.multiline_text(
        (x0 + 50, y0 + 1335),
        "\n".join(inspection_points),
        font=load_font(28),
        fill="#4b5563",
        spacing=10,
    )
    rule_box = (x0 + 35, y0 + 2150, x1 - 35, y0 + 2440)
    draw.rounded_rectangle(
        rule_box,
        radius=18,
        fill="#eef2ff",
        outline="#c7d2fe",
        width=2,
    )
    draw.multiline_text(
        (rule_box[0] + 30, rule_box[1] + 35),
        "Reviewer rule:\n"
        "Use the small context image only for silhouette/length and presence.\n"
        "Use both crops for logos, geometry, closures, seams, and material.",
        font=load_font(25),
        fill="#312e81",
        spacing=12,
    )


def render_development_case(
    development_root: Path,
    output_root: Path,
    case_id: str,
) -> Path:
    config = DEVELOPMENT_CASES[case_id]
    width, height = 4500, 2800
    canvas = Image.new("RGB", (width, height), "#f3f5f7")
    draw = ImageDraw.Draw(canvas)

    draw.text(
        (70, 35),
        f"{case_id} review sheet — {config['title']}",
        font=load_font(66, bold=True),
        fill="#111827",
    )
    draw.text(
        (70, 120),
        "Rate the garment crops first. Ignore pose, stance, facial expression, "
        "and scene lighting unless they hide garment details.",
        font=load_font(30),
        fill="#374151",
    )

    source = load_development_source(development_root, case_id)
    draw_source_column(
        canvas,
        draw,
        source,
        (50, 210, 1040, 2720),
        config["inspect"],
    )

    x_positions = (1090, 2235, 3380)
    images = load_development_images(development_root, case_id)
    for x, (label, image) in zip(x_positions, images, strict=True):
        panel_box = (x, 210, x + 1070, 2720)
        draw_panel(draw, panel_box)
        draw.text(
            (x + 35, 250),
            label,
            font=load_font(44, bold=True),
            fill="#111827",
        )
        draw.text(
            (x + 35, 308),
            "Context image only",
            font=load_font(26),
            fill="#6b7280",
        )
        paste_center(canvas, image, (x + 120, 350, x + 950, 980))

        draw.text(
            (x + 35, 1035),
            "Primary garment crop — rate this first",
            font=load_font(31, bold=True),
            fill="#111827",
        )
        primary = clarify(crop_normalized(image, config["primary"]))
        primary_box = (x + 40, 1090, x + 1030, 1840)
        paste_center(canvas, primary, primary_box)
        draw.rounded_rectangle(
            primary_box,
            radius=16,
            outline="#9ca3af",
            width=3,
        )

        draw.text(
            (x + 35, 1895),
            "Detail zoom",
            font=load_font(31, bold=True),
            fill="#111827",
        )
        detail = clarify(crop_normalized(image, config["detail"]))
        detail_box = (x + 170, 1960, x + 900, 2580)
        paste_center(canvas, detail, detail_box)
        draw.rounded_rectangle(
            detail_box,
            radius=16,
            outline="#9ca3af",
            width=3,
        )
        image.close()

    output_path = output_root / f"{case_id}-human-review.png"
    canvas.save(output_path, "PNG", optimize=True)
    return output_path


def render_holdout_case(
    holdout_root: Path,
    output_root: Path,
    case_id: str,
) -> Path:
    config = HOLDOUT_CASES[case_id]
    width, height = 3400, 2500
    canvas = Image.new("RGB", (width, height), "#f3f5f7")
    draw = ImageDraw.Draw(canvas)

    draw.text(
        (70, 35),
        f"{case_id} review sheet — {config['title']}",
        font=load_font(64, bold=True),
        fill="#111827",
    )
    draw.text(
        (70, 115),
        "Frozen baseline only. Rate the garment crops first. Ignore model "
        "lighting and pose unless they block garment details.",
        font=load_font(29),
        fill="#374151",
    )

    source_box = (50, 210, 1040, 2420)
    result_box = (1090, 210, 3340, 2420)
    draw_panel(draw, source_box)
    draw_panel(draw, result_box)

    source = load_holdout_source(holdout_root, case_id)
    draw.text(
        (85, 250),
        "Source garment",
        font=load_font(42, bold=True),
        fill="#111827",
    )
    paste_center(canvas, source, (100, 330, 990, 1200))
    draw.text(
        (100, 1260),
        "Ground-truth packshot",
        font=load_font(30, bold=True),
        fill="#111827",
    )
    draw.multiline_text(
        (100, 1310),
        "Use this as the reference.\nInspect identity-critical product details.",
        font=load_font(27),
        fill="#4b5563",
        spacing=12,
    )
    draw.text(
        (100, 1465),
        "What to inspect",
        font=load_font(30, bold=True),
        fill="#111827",
    )
    draw.multiline_text(
        (100, 1520),
        "\n".join(config["inspect"]),
        font=load_font(28),
        fill="#4b5563",
        spacing=10,
    )

    image_path = (
        holdout_root
        / case_id
        / "google_gemini-3.1-flash-lite-image"
        / "baseline"
        / "image.jpg"
    )
    with Image.open(image_path) as raw:
        image = raw.convert("RGB")
        draw.text(
            (1125, 250),
            "Frozen baseline",
            font=load_font(42, bold=True),
            fill="#111827",
        )
        draw.text(
            (1125, 308),
            "Context image only",
            font=load_font(26),
            fill="#6b7280",
        )
        paste_center(canvas, image, (1180, 350, 2000, 1020))

        draw.text(
            (1125, 1080),
            "Primary garment crop — rate this first",
            font=load_font(31, bold=True),
            fill="#111827",
        )
        primary = clarify(crop_normalized(image, config["primary"]))
        primary_box = (1130, 1140, 2220, 1910)
        paste_center(canvas, primary, primary_box)
        draw.rounded_rectangle(
            primary_box,
            radius=16,
            outline="#9ca3af",
            width=3,
        )

        draw.text(
            (2350, 1080),
            "Detail zoom",
            font=load_font(31, bold=True),
            fill="#111827",
        )
        detail = clarify(crop_normalized(image, config["detail"]))
        detail_box = (2360, 1140, 3290, 1910)
        paste_center(canvas, detail, detail_box)
        draw.rounded_rectangle(
            detail_box,
            radius=16,
            outline="#9ca3af",
            width=3,
        )

    rule_box = (1130, 1980, 3290, 2340)
    draw.rounded_rectangle(
        rule_box,
        radius=18,
        fill="#eef2ff",
        outline="#c7d2fe",
        width=2,
    )
    draw.multiline_text(
        (1160, 2020),
        "Reviewer rule:\n"
        "Use the full image only for silhouette/length and presence.\n"
        "Use both crops for logos, geometry, closures, seams, and material.\n"
        "Do not infer quality from the automatic score.",
        font=load_font(25),
        fill="#312e81",
        spacing=12,
    )

    output_path = output_root / f"{case_id}-human-review.png"
    canvas.save(output_path, "PNG", optimize=True)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development-root", type=Path, required=True)
    parser.add_argument("--holdout-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [
        render_development_case(args.development_root, args.output_dir, case_id)
        for case_id in ("D01", "D02", "D03")
    ]
    outputs.extend(
        render_holdout_case(args.holdout_root, args.output_dir, case_id)
        for case_id in ("H01", "H02")
    )
    for output in outputs:
        with Image.open(output) as image:
            print(f"{output.name}: {image.size}, {output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
