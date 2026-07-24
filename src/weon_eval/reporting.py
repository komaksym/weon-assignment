"""Persist development comparisons and create compact visual evidence."""

from __future__ import annotations

import csv
import json
import shutil
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from weon_eval.evaluation import mean_score
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS
from weon_eval.vlm import JsonResult


def image_path(result_dir: Path) -> Path:
    images = [
        path
        for path in result_dir.glob("image.*")
        if path.suffix in {".jpg", ".png", ".webp"}
    ]
    if len(images) != 1:
        raise ValueError(f"expected one generated image in {result_dir}")
    return images[0]


def metadata(result_dir: Path) -> dict[str, object]:
    payload: object = json.loads((result_dir / "metadata.json").read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"invalid metadata in {result_dir}")
    return payload


def decimal_value(value: object) -> Decimal:
    return Decimal("0") if value is None else Decimal(str(value))


def float_value(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"invalid numeric metadata value: {value}")
    return float(value)


def write_best_of_two(
    *,
    case_root: Path,
    selected: str,
    structured_a_dir: Path,
    structured_b_dir: Path,
    evaluation: JsonResult,
) -> Path:
    source_dir = structured_a_dir if selected == "structured_a" else structured_b_dir
    source_image = image_path(source_dir)
    result_dir = case_root / "best_of_two"
    result_dir.mkdir()
    target = result_dir / f"image{source_image.suffix}"
    shutil.copyfile(source_image, target)
    (result_dir / "selection.json").write_text(
        json.dumps(
            {
                "selected": selected,
                "source": str(source_image),
                "selection_cost_usd": (
                    str(evaluation.cost_usd) if evaluation.cost_usd is not None else None
                ),
                "selection_latency_seconds": evaluation.latency_seconds,
            },
            indent=2,
        )
        + "\n"
    )
    return result_dir


def _panel(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    contained = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
    panel = Image.new("RGB", size, "white")
    offset = ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2)
    panel.paste(contained, offset)
    return panel


def write_contact_sheet(
    *,
    garment: Path,
    baseline: Path,
    structured_a: Path,
    structured_b: Path,
    selected: str,
    output: Path,
) -> None:
    panel_size = (320, 420)
    label_height = 36
    items = (
        ("garment reference", garment),
        ("baseline", baseline),
        ("structured", structured_a),
        ("candidate B", structured_b),
        (
            f"best of two ({selected[-1].upper()})",
            structured_a if selected == "structured_a" else structured_b,
        ),
    )
    sheet = Image.new(
        "RGB",
        (panel_size[0] * len(items), panel_size[1] + label_height),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    for index, (label, path) in enumerate(items):
        x = index * panel_size[0]
        sheet.paste(_panel(path, panel_size), (x, 0))
        draw.text((x + 8, panel_size[1] + 10), label, fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="JPEG", quality=90)


def result_row(
    *,
    case_id: str,
    strategy: str,
    candidate: str,
    scores: Mapping[str, float],
    run_metadata: Mapping[str, object],
    summary: str,
    attribute_metadata: Mapping[str, object] | None = None,
    selection_metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    generation_cost = decimal_value(run_metadata.get("cost_usd"))
    generation_latency = float_value(run_metadata.get("latency_seconds"))
    attribute_cost = (
        decimal_value(attribute_metadata.get("cost_usd"))
        if attribute_metadata
        else Decimal("0")
    )
    attribute_latency = (
        float_value(attribute_metadata.get("latency_seconds"))
        if attribute_metadata
        else 0.0
    )
    selection_cost = (
        decimal_value(selection_metadata.get("selection_cost_usd"))
        if selection_metadata
        else Decimal("0")
    )
    selection_latency = (
        float_value(selection_metadata.get("selection_latency_seconds"))
        if selection_metadata
        else 0.0
    )
    row: dict[str, object] = {
        "case_id": case_id,
        "strategy": strategy,
        "candidate": candidate,
        "mean_auto_score": mean_score(scores),
        "generation_cost_usd": str(generation_cost),
        "attribute_extraction_cost_usd": str(attribute_cost),
        "selection_cost_usd": str(selection_cost),
        "total_strategy_cost_usd": str(generation_cost + attribute_cost + selection_cost),
        "generation_latency_seconds": generation_latency,
        "attribute_extraction_latency_seconds": attribute_latency,
        "selection_latency_seconds": selection_latency,
        "total_strategy_latency_seconds": (
            generation_latency + attribute_latency + selection_latency
        ),
        "auto_summary": summary,
    }
    row.update(scores)
    return row


def write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise ValueError("cannot write empty results")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def manual_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "case_id": row["case_id"],
            "strategy": row["strategy"],
            **{dimension: "" for dimension in ATTRIBUTE_DIMENSIONS},
            "mean_manual_score": "",
            "selector_agrees": "" if row["strategy"] == "best_of_two" else "n/a",
            "notes": "",
        }
        for row in rows
    ]


def strategy_means(rows: Sequence[Mapping[str, object]]) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        strategy = str(row["strategy"])
        grouped.setdefault(strategy, []).append(float_value(row["mean_auto_score"]))
    return {strategy: sum(values) / len(values) for strategy, values in grouped.items()}
