"""Run the frozen H01-H02 baseline and persist final evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from weon_eval.cases import Case, load_cases
from weon_eval.evaluation import JsonRequester, mean_score, parse_scores, summary_text
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS, render_prompt
from weon_eval.reporting import decimal_value, float_value, image_path, metadata, write_csv
from weon_eval.runner import Generator, run_case
from weon_eval.vlm import request_json

HOLDOUT_CASE_IDS = ("H01", "H02")
DEFAULT_GENERATOR_MODEL = "google/gemini-3.1-flash-lite-image"
DEFAULT_EVALUATOR_MODEL = "openai/gpt-4.1-mini"


def _holdout_cases(cases_path: Path) -> list[Case]:
    cases = load_cases(cases_path)
    selected: list[Case] = []
    for case_id in HOLDOUT_CASE_IDS:
        case = cases[case_id]
        if case.split != "holdout":
            raise ValueError(f"{case_id} is not a holdout case")
        selected.append(case)
    return selected


def _candidate_schema() -> dict[str, object]:
    scores = {
        dimension: {"type": "number", "enum": [-1, 0, 0.5, 1]}
        for dimension in ATTRIBUTE_DIMENSIONS
    }
    candidate = {
        "type": "object",
        "properties": {
            "scores": {
                "type": "object",
                "properties": scores,
                "required": list(ATTRIBUTE_DIMENSIONS),
                "additionalProperties": False,
            },
            "summary": {"type": "string", "minLength": 1},
        },
        "required": ["scores", "summary"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"candidate_1": candidate},
        "required": ["candidate_1"],
        "additionalProperties": False,
    }


def _evaluation_prompt() -> str:
    return (
        "Image order: garment packshot(s), candidate_1. The candidate identity is opaque. "
        "Judge candidate_1 only against the garment packshot on color, print/logo, "
        "silhouette/length, construction details, texture/material, and garment presence. "
        "Use 1 for preserved, 0.5 for partial, 0 for drifted, and -1 only when the source "
        "attribute is genuinely not applicable. Do not reward overall aesthetics."
    )


def _panel(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    contained = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
    panel = Image.new("RGB", size, "white")
    offset = ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2)
    panel.paste(contained, offset)
    return panel


def _write_contact_sheet(*, garment: Path, result: Path, output: Path) -> None:
    panel_size = (420, 540)
    label_height = 42
    items = (("garment packshot", garment), ("frozen baseline result", result))
    sheet = Image.new(
        "RGB",
        (panel_size[0] * len(items), panel_size[1] + label_height),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    for index, (label, path) in enumerate(items):
        x = index * panel_size[0]
        sheet.paste(_panel(path, panel_size), (x, 0))
        draw.text((x + 10, panel_size[1] + 12), label, fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="JPEG", quality=88, optimize=True)


def _result_row(
    *,
    case_id: str,
    scores: Mapping[str, float],
    run_metadata: Mapping[str, object],
    evaluation_cost: Decimal | None,
    evaluation_latency: float,
    summary: str,
) -> dict[str, object]:
    generation_cost = decimal_value(run_metadata.get("cost_usd"))
    generation_latency = float_value(run_metadata.get("latency_seconds"))
    score_cost = evaluation_cost or Decimal("0")
    row: dict[str, object] = {
        "case_id": case_id,
        "strategy": "baseline",
        "candidate": "candidate_1",
        "mean_auto_score": mean_score(scores),
        "generation_cost_usd": str(generation_cost),
        "evaluation_cost_usd": str(score_cost),
        "total_experiment_cost_usd": str(generation_cost + score_cost),
        "generation_latency_seconds": generation_latency,
        "evaluation_latency_seconds": evaluation_latency,
        "total_experiment_latency_seconds": generation_latency + evaluation_latency,
        "auto_summary": summary,
    }
    row.update(scores)
    return row


def _manual_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "case_id": row["case_id"],
            "strategy": "baseline",
            **{dimension: "" for dimension in ATTRIBUTE_DIMENSIONS},
            "mean_manual_score": "",
            "notes": "",
        }
        for row in rows
    ]


def run_holdouts(
    *,
    cases_path: Path,
    prompt_path: Path,
    api_key: str,
    output_root: Path,
    generator_model: str = DEFAULT_GENERATOR_MODEL,
    evaluator_model: str = DEFAULT_EVALUATOR_MODEL,
    generator: Generator,
    requester: JsonRequester = request_json,
) -> Path:
    """Run the frozen baseline once on H01 and H02, without development access."""

    if output_root.exists():
        raise FileExistsError(f"output already exists: {output_root}")
    cases = _holdout_cases(cases_path)
    output_root.mkdir(parents=True)

    rows: list[dict[str, object]] = []
    generation_cost = Decimal("0")
    evaluation_cost = Decimal("0")
    generation_latency = 0.0
    evaluation_latency = 0.0

    for case in cases:
        prompt = render_prompt(case, prompt_path)
        result_dir = run_case(
            case=case,
            prompt=prompt,
            model=generator_model,
            strategy="baseline",
            api_key=api_key,
            output_root=output_root,
            generator=generator,
        )
        generated_image = image_path(result_dir)
        evaluation = requester(
            model=evaluator_model,
            prompt=_evaluation_prompt(),
            image_paths=(*case.garments, generated_image),
            schema_name="holdout_candidate",
            schema=_candidate_schema(),
            api_key=api_key,
        )
        scores = parse_scores(evaluation.data, "candidate_1")
        run_metadata = metadata(result_dir)
        row = _result_row(
            case_id=case.id,
            scores=scores,
            run_metadata=run_metadata,
            evaluation_cost=evaluation.cost_usd,
            evaluation_latency=evaluation.latency_seconds,
            summary=summary_text(evaluation.data, "candidate_1"),
        )
        rows.append(row)

        case_root = output_root / case.id
        (case_root / "evaluation.json").write_text(
            json.dumps(
                {
                    "candidate_id": "candidate_1",
                    "evaluation": evaluation.data,
                    "evaluator_model": evaluator_model,
                    "cost_usd": (
                        str(evaluation.cost_usd) if evaluation.cost_usd is not None else None
                    ),
                    "latency_seconds": evaluation.latency_seconds,
                },
                indent=2,
            )
            + "\n"
        )
        _write_contact_sheet(
            garment=case.garments[0],
            result=generated_image,
            output=case_root / "contact_sheet.jpg",
        )

        generation_cost += decimal_value(run_metadata.get("cost_usd"))
        generation_latency += float_value(run_metadata.get("latency_seconds"))
        evaluation_cost += evaluation.cost_usd or Decimal("0")
        evaluation_latency += evaluation.latency_seconds

    write_csv(output_root / "results.csv", rows)
    write_csv(output_root / "manual_scores.csv", _manual_rows(rows))
    (output_root / "holdout_summary.json").write_text(
        json.dumps(
            {
                "cases": list(HOLDOUT_CASE_IDS),
                "strategy": "baseline",
                "generator_model": generator_model,
                "evaluator_model": evaluator_model,
                "image_requests": 2,
                "evaluation_requests": 2,
                "development_requests": 0,
                "automatic_retries": 0,
                "total_generation_cost_usd": str(generation_cost),
                "total_evaluation_cost_usd": str(evaluation_cost),
                "total_experiment_cost_usd": str(generation_cost + evaluation_cost),
                "total_generation_latency_seconds": generation_latency,
                "total_evaluation_latency_seconds": evaluation_latency,
                "mean_auto_score": sum(
                    float_value(row["mean_auto_score"]) for row in rows
                )
                / len(rows),
                "status": "frozen - pending manual sanity check",
            },
            indent=2,
        )
        + "\n"
    )
    return output_root
