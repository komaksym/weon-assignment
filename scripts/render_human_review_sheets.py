from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_REG = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
FONT_BOLD = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')

DEV_SOURCE_BOXES = {
    'D01': (0, 38, 310, 382),
    'D02': (12, 166, 308, 326),
    'D03': (5, 38, 315, 360),
}
DEV_CROPS = {
    'D01': (0.22, 0.34, 0.78, 0.66),
    'D02': (0.20, 0.70, 0.80, 0.99),
    'D03': (0.18, 0.16, 0.82, 0.72),
}
HOLDOUT_SOURCE_BOXES = {
    'H01': (15, 198, 405, 415),
    'H02': (5, 35, 415, 492),
}
HOLDOUT_CROPS = {
    'H01': (206, 924, 699, 1188),
    'H02': (260, 468, 636, 828),
}
CASE_NAMES = {
    'D01': 'Technical shorts',
    'D02': 'Low-top shoes',
    'D03': 'Waxed jacket',
    'H01': 'Footwear holdout',
    'H02': 'Shorts holdout',
}


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), size)


def fit(image: Image.Image, box: tuple[int, int]) -> Image.Image:
    max_width, max_height = box
    scale = min(max_width / image.width, max_height / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def paste_center(
    canvas: Image.Image,
    image: Image.Image,
    box: tuple[int, int, int, int],
) -> None:
    x0, y0, x1, y1 = box
    fitted = fit(image, (x1 - x0, y1 - y0))
    x = x0 + (x1 - x0 - fitted.width) // 2
    y = y0 + (y1 - y0 - fitted.height) // 2
    canvas.paste(fitted, (x, y))


def draw_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle(box, radius=20, fill='white', outline='#c9ced6', width=3)


def crop_normalized(
    image: Image.Image,
    box: tuple[float, float, float, float],
) -> Image.Image:
    width, height = image.size
    x0, y0, x1, y1 = box
    return image.crop(
        (round(x0 * width), round(y0 * height), round(x1 * width), round(y1 * height))
    )


def development_source(root: Path, case: str) -> Image.Image:
    with Image.open(root / case / 'contact_sheet.jpg') as sheet:
        return sheet.crop(DEV_SOURCE_BOXES[case]).convert('RGB')


def development_images(root: Path, case: str) -> list[tuple[str, Image.Image]]:
    case_dir = root / case
    paths = [
        (
            'Baseline',
            case_dir / 'google_gemini-3.1-flash-lite-image' / 'baseline' / 'image.jpg',
        ),
        (
            'Structured',
            case_dir / 'google_gemini-3.1-flash-lite-image' / 'structured_a' / 'image.jpg',
        ),
        ('Best of two', case_dir / 'best_of_two' / 'image.jpg'),
    ]
    return [(label, Image.open(path).convert('RGB')) for label, path in paths]


def render_development(root: Path, output_dir: Path, case: str) -> Path:
    width, height = 4200, 2400
    canvas = Image.new('RGB', (width, height), '#f3f5f7')
    draw = ImageDraw.Draw(canvas)

    draw.text(
        (80, 42),
        f'{case} human-review sheet — {CASE_NAMES[case]}',
        font=font(62, bold=True),
        fill='#111827',
    )
    draw.text(
        (80, 122),
        'Open at full size. Compare garment identity—not scene realism. '
        'Inspect logos, geometry, closures, seams, and material.',
        font=font(30),
        fill='#374151',
    )

    source_box = (60, 220, 960, 2260)
    draw_panel(draw, source_box)
    draw.text((100, 255), 'Source garment', font=font(42, bold=True), fill='#111827')
    source = development_source(root, case)
    paste_center(canvas, source, (110, 340, 910, 1350))
    draw.text((110, 1430), 'Reference packshot', font=font(32, bold=True), fill='#111827')
    draw.multiline_text(
        (110, 1490),
        'Use this as ground truth.\nA plausible garment is not enough:\n'
        'identity-critical details must match.',
        font=font(28),
        fill='#4b5563',
        spacing=12,
    )

    images = development_images(root, case)
    for x, (label, image) in zip((1000, 2060, 3120), images, strict=True):
        box = (x, 220, x + 1020, 2260)
        draw_panel(draw, box)
        draw.text((x + 40, 255), label, font=font(42, bold=True), fill='#111827')
        draw.text((x + 40, 315), 'Full generated image', font=font(26), fill='#6b7280')
        paste_center(canvas, image, (x + 95, 365, x + 925, 1320))

        draw.text(
            (x + 40, 1370),
            'Garment detail crop',
            font=font(30, bold=True),
            fill='#111827',
        )
        detail = crop_normalized(image, DEV_CROPS[case])
        detail_box = (x + 45, 1430, x + 975, 2180)
        paste_center(canvas, detail, detail_box)
        draw.rounded_rectangle(detail_box, radius=14, outline='#9ca3af', width=3)

    output = output_dir / f'{case}-human-review.png'
    canvas.save(output, 'PNG', optimize=True)
    for _, image in images:
        image.close()
    return output


def holdout_source(root: Path, case: str) -> Image.Image:
    with Image.open(root / case / 'contact_sheet.jpg') as sheet:
        return sheet.crop(HOLDOUT_SOURCE_BOXES[case]).convert('RGB')


def render_holdout(root: Path, output_dir: Path, case: str) -> Path:
    width, height = 3100, 2250
    canvas = Image.new('RGB', (width, height), '#f3f5f7')
    draw = ImageDraw.Draw(canvas)

    draw.text(
        (80, 42),
        f'{case} human-review sheet — {CASE_NAMES[case]}',
        font=font(62, bold=True),
        fill='#111827',
    )
    draw.text(
        (80, 122),
        'Frozen baseline output. Compare exact product identity against the source; '
        'do not infer quality from the automatic score.',
        font=font(30),
        fill='#374151',
    )

    for box in (
        (60, 220, 1000, 2140),
        (1050, 220, 2040, 2140),
        (2090, 220, 3040, 2140),
    ):
        draw_panel(draw, box)

    draw.text((100, 255), 'Source garment', font=font(42, bold=True), fill='#111827')
    source = holdout_source(root, case)
    paste_center(canvas, source, (110, 350, 950, 1500))
    draw.multiline_text(
        (110, 1580),
        'Ground truth packshot.\nInspect branding, silhouette,\nconstruction, and material.',
        font=font(28),
        fill='#4b5563',
        spacing=12,
    )

    image_path = (
        root / case / 'google_gemini-3.1-flash-lite-image' / 'baseline' / 'image.jpg'
    )
    with Image.open(image_path) as raw:
        image = raw.convert('RGB')
        draw.text(
            (1090, 255),
            'Frozen baseline — full image',
            font=font(40, bold=True),
            fill='#111827',
        )
        paste_center(canvas, image, (1130, 350, 1960, 1990))

        draw.text(
            (2130, 255),
            'Frozen baseline — detail crop',
            font=font(40, bold=True),
            fill='#111827',
        )
        crop = image.crop(HOLDOUT_CROPS[case])
        detail_box = (2140, 390, 2990, 1600)
        paste_center(canvas, crop, detail_box)
        draw.rounded_rectangle(detail_box, radius=14, outline='#9ca3af', width=3)
        draw.multiline_text(
            (2140, 1680),
            'Rate visible fidelity here.\nUse the full image only for overall\n'
            'silhouette, length, and presence.',
            font=font(28),
            fill='#4b5563',
            spacing=12,
        )

    output = output_dir / f'{case}-human-review.png'
    canvas.save(output, 'PNG', optimize=True)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Render high-resolution human-review sheets.')
    parser.add_argument('--development-root', type=Path, required=True)
    parser.add_argument('--holdout-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [
        render_development(args.development_root, args.output_dir, case)
        for case in ('D01', 'D02', 'D03')
    ]
    outputs.extend(
        render_holdout(args.holdout_root, args.output_dir, case) for case in ('H01', 'H02')
    )
    for path in outputs:
        with Image.open(path) as image:
            print(f'{path.name}: {image.size}, {path.stat().st_size} bytes')


if __name__ == '__main__':
    main()
