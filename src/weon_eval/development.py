"""Run the complete D01-D03 development experiment matrix."""

from __future__ import annotations

import csv
import json
import shutil
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageDraw, ImageOps

from weon_eval.cases import Case, load_cases
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS, render_prompt, render_structured_prompt
from weon_eval.runner import Generator, run_case
from weon_eval.vlm import JsonResult, request_json

DEVELOPMENT_CASE_IDS = ("D01", "D02", "D03")
DEFAULT_GENERATOR_MODEL = "google/gemini-3.1-flash-lite-image"
DEFAULT_EVALUATOR_MODEL = "google/gemini-2.5-flash-lite"
_ALLOWED_SCORES = {-1.0, 0.0, 0.5, 1.0}


class JsonRequester(Protocol):
    """Callable boundary used for testable VLM requests."""

    def __call__(
        self,
        *,
        model: str,
        prompt: str,
        image_paths: Sequence[Path],
        schema_name: str,
        schema: Mapping[str, object],
        api_key: str,
    ) -> JsonResult: ...


def _attribute_schema() -> dict[str, object]:
    properties = {
        dimension: {"type": "string", "minLength": 1}
        for dimension in ATTRIBUTE_DIMENSIONS
    }
    return {
        "type": "object",
        "properties": {
            "attributes": {
                "type": "object",
                "properties": properties,
                "required": list(ATTRIBUTE_DIMENSIONS),
                "additionalProperties": False,
            }
        },
        "required": ["attributes"],
        "additionalProperties": False,
    }


def _candidate_schema() -> dict[str, object]:
    score_properties = {
        dimension: {"type": "number", "enum": [-1, 0, 0.5, 1]}
        for dimension in ATTRIBUTE_DIMENSIONS
    }
    return {
        "type": "object",
        "properties": {
            "scores": {
                "type": "object",
                "properties": score_properties,
                "required": list(ATTRIBUTE_DIMENSIONS),
                "additionalProperties": False,
            },
            "summary": {"type": "string", "minLength": 1},
        },
        "required": ["scores", "summary"],
        "additionalProperties": False,
    }


def _evaluation_schema() -> dict[str, object]:
    candidate = _candidate_schema()
    return {
        "type": "object",
        "properties": {
            "baseline": candidate,
            "structured_a": candidate,
            "structured_b": candidate,
        },
        "required": ["baseline", "structured_a", "structured_b"],
        "additionalProperties": False,
    }


def _attributes(data: Mapping[str, object]) -> dict[str, str]:
    raw = data.get("attributes")
    if not isinstance(raw, dict):
        raise ValueError("attribute evaluator returned no attributes")
    attributes: dict[str, str] = {}
    for dimension in ATTRIBUTE_DIMENSIONS:
        value = raw.get(dimension)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"attribute evaluator returned invalid {dimension}")
        attributes[dimension] = value.strip()
    return attributes


def _scores(data: Mapping[str, object], candidate: str) -> dict[str, float]:
    raw_candidate = data.get(candidate)
    if not isinstance(raw_candidate, dict):
        raise ValueError(f"evaluator returned no {candidate} result")
    raw_scores = raw_candidate.get("scores")
    if not isinstance(raw_scores, dict):
        raise ValueError(f"evaluator returned no {candidate} scores")
    scores: dict[str, float] = {}
    for dimension in ATTRIBUTE_DIMENSIONS:
        raw_score = raw_scores.get(dimension)
        if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
            raise ValueError(f"evaluator returned invalid {candidate} {dimension} score")
        score = float(raw_score)
        if score not in _ALLOWED_SCORES:
            raise ValueError(f"evaluator returned unsupported score: {score}")
        scores[dimension] = score
    return scores


def mean_score(scores: Mapping[str, float]) -> float:
    """Average applicable 0/0.5/1 scores, ignoring -1 (N/A)."""

    applicable = [score for score in scores.values() if score >= 0]
    if not applicable:
        raise ValueError("candidate has no applicable evaluation dimensions")
    return sum(applicable) / len(applicable)


def choose_best(structured_a: Mapping[str, float], structured_b: Mapping[str, float]) -> str:
    """Select the higher VLM score, breaking ties toward candidate A."""

    if mean_score(structured_a) >= mean_score(structured_b):
        return "structured_a"
    return "structured_b"


def _image_path(result_dir: Path) -> Path:
    images = [
        path
        for path in result_dir.glob("image.*")
        if path.suffix in {".jpg", ".png", ".webp"}
    ]
    if len(images) != 1:
        raise ValueError(f"expected one generated image in {result_dir}")
    return images[0]


def _metadata(result_dir: Path) -> dict[str, object]:
    payload: object = json.loads((result_dir / "metadata.json").read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"invalid metadata in {result_dir}")
    return payload


def _decimal(value: object) -> Decimal:
    return Decimal("0") if value is None else Decimal(str(value))


def _float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"invalid numeric metadata value: {value}")
    return float(value)


def _best_of_two(
    *,
    case_root: Path,
    selected: str,
    structured_a_dir: Path,
    structured_b_dir: Path,
    evaluation: JsonResult,
) -> Path:
    source_dir = structured_a_dir if selected == "structured_a" else structured_b_dir
    source_image = _image_path(source_dir)
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
    panel.paste(contained, ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2))
    return panel


def _contact_sheet(
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


def _summary_text(data: Mapping[str, object], candidate: str) -> str:
    raw = data.get(candidate)
    if not isinstance(raw, dict) or not isinstance(raw.get("summary"), str):
        raise ValueError(f"evaluator returned no {candidate} summary")
    return str(raw["summary"])


def _result_row(
    *,
    case_id: str,
    strategy: str,
    candidate: str,
    scores: Mapping[str, float],
    metadata: Mapping[str, object],
    extra_metadata: Mapping[str, object] | None = None,
    summary: str,
) -> dict[str, object]:
    generation_cost = _decimal(metadata.get("cost_usd"))
    generation_latency = _float(metadata.get("latency_seconds"))
    selection_cost = (
        _decimal(extra_metadata.get("selection_cost_usd"))
        if extra_metadata
        else Decimal("0")
    )
    selection_latency = (
        _float(extra_metadata.get("selection_latency_seconds")) if extra_metadata else 0.0
    )
    row: dict[str, object] = {
        "case_id": case_id,
        "strategy": strategy,
        "candidate": candidate,
        "mean_auto_score": mean_score(scores),
        "generation_cost_usd": str(generation_cost),
        "selection_cost_usd": str(selection_cost),
        "total_strategy_cost_usd": str(generation_cost + selection_cost),
        "generation_latency_seconds": generation_latency,
        "selection_latency_seconds": selection_latency,
        "total_strategy_latency_seconds": generation_latency + selection_latency,
        "auto_summary": summary,
    }
    row.update(scores)
    return row


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise ValueError("cannot write empty results")
    fieldnames = list(rows[0])
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _manual_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
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


def _strategy_means(rows: Sequence[Mapping[str, object]]) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        strategy = str(row["strategy"])
        grouped.setdefault(strategy, []).append(float(row["mean_auto_score"]))
    return {strategy: sum(values) / len(values) for strategy, values in grouped.items()}


def run_development(
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
    """Run nine image calls and six VLM calls across D01-D03 without holdouts."""

    if output_root.exists():
        raise FileExistsError(f"output already exists: {output_root}")
    cases = load_cases(cases_path)
    selected_cases: list[Case] = []
    for case_id in DEVELOPMENT_CASE_IDS:
        case = cases[case_id]
        if case.split != "development":
            raise ValueError(f"{case_id} is not a development case")
        selected_cases.append(case)

    output_root.mkdir(parents=True)
    rows: list[dict[str, object]] = []
    attribute_cost = Decimal("0")
    attribute_latency = 0.0
    actual_generation_cost = Decimal("0")
    actual_generation_latency = 0.0
    actual_selection_cost = Decimal("0")
    actual_selection_latency = 0.0
    for case in selected_cases:
        case_root = output_root / case.id
        case_root.mkdir()
        attribute_result = requester(
            model=evaluator_model,
            prompt=(
                "Inspect only the garment packshot image(s). Describe the visible garment facts "
                "for the requested dimensions. Use 'not visible' when a detail cannot be seen; "
                "do not infer hidden details."
            ),
            image_paths=case.garments,
            schema_name="garment_attributes",
            schema=_attribute_schema(),
            api_key=api_key,
        )
        attributes = _attributes(attribute_result.data)
        attribute_cost += attribute_result.cost_usd or Decimal("0")
        attribute_latency += attribute_result.latency_seconds
        (case_root / "attributes.json").write_text(
            json.dumps(
                {
                    "attributes": attributes,
                    "cost_usd": (
                        str(attribute_result.cost_usd)
                        if attribute_result.cost_usd is not None
                        else None
                    ),
                    "latency_seconds": attribute_result.latency_seconds,
                    "model": evaluator_model,
                },
                indent=2,
            )
            + "\n"
        )

        baseline_prompt = render_prompt(case, prompt_path)
        structured_prompt = render_structured_prompt(case, prompt_path, attributes)
        baseline_dir = run_case(
            case=case,
            prompt=baseline_prompt,
            model=generator_model,
            strategy="baseline",
            api_key=api_key,
            output_root=output_root,
            generator=generator,
        )
        structured_a_dir = run_case(
            case=case,
            prompt=structured_prompt,
            model=generator_model,
            strategy="structured_a",
            api_key=api_key,
            output_root=output_root,
            generator=generator,
        )
        structured_b_dir = run_case(
            case=case,
            prompt=structured_prompt,
            model=generator_model,
            strategy="structured_b",
            api_key=api_key,
            output_root=output_root,
            generator=generator,
        )

        baseline_image = _image_path(baseline_dir)
        structured_a_image = _image_path(structured_a_dir)
        structured_b_image = _image_path(structured_b_dir)
        evaluation = requester(
            model=evaluator_model,
            prompt=(
                "Image order: garment packshot, baseline result, structured candidate A, "
                "structured candidate B. Score each result against the garment packshot on "
                "color, print/logo, silhouette/length, construction details, texture/material, "
                "and garment presence. Use 1 for preserved, 0.5 for partial, 0 for drifted, "
                "and -1 only when the source attribute is genuinely not applicable."
            ),
            image_paths=(
                *case.garments,
                baseline_image,
                structured_a_image,
                structured_b_image,
            ),
            schema_name="garment_comparison",
            schema=_evaluation_schema(),
            api_key=api_key,
        )
        baseline_scores = _scores(evaluation.data, "baseline")
        structured_a_scores = _scores(evaluation.data, "structured_a")
        structured_b_scores = _scores(evaluation.data, "structured_b")
        selected = choose_best(structured_a_scores, structured_b_scores)
        best_dir = _best_of_two(
            case_root=case_root,
            selected=selected,
            structured_a_dir=structured_a_dir,
            structured_b_dir=structured_b_dir,
            evaluation=evaluation,
        )
        _contact_sheet(
            garment=case.garments[0],
            baseline=baseline_image,
            structured_a=structured_a_image,
            structured_b=structured_b_image,
            selected=selected,
            output=case_root / "contact_sheet.jpg",
        )

        baseline_metadata = _metadata(baseline_dir)
        structured_a_metadata = _metadata(structured_a_dir)
        structured_b_metadata = _metadata(structured_b_dir)
        for unique_metadata in (
            baseline_metadata,
            structured_a_metadata,
            structured_b_metadata,
        ):
            actual_generation_cost += _decimal(unique_metadata.get("cost_usd"))
            actual_generation_latency += _float(unique_metadata.get("latency_seconds"))
        actual_selection_cost += evaluation.cost_usd or Decimal("0")
        actual_selection_latency += evaluation.latency_seconds
        selected_scores = (
            structured_a_scores if selected == "structured_a" else structured_b_scores
        )
        selected_summary = _summary_text(evaluation.data, selected)
        selection_metadata: dict[str, object] = {
            "selection_cost_usd": (
                str(evaluation.cost_usd) if evaluation.cost_usd is not None else None
            ),
            "selection_latency_seconds": evaluation.latency_seconds,
        }
        combined_generation_metadata: dict[str, object] = {
            "cost_usd": str(
                _decimal(structured_a_metadata.get("cost_usd"))
                + _decimal(structured_b_metadata.get("cost_usd"))
            ),
            "latency_seconds": _float(structured_a_metadata.get("latency_seconds"))
            + _float(structured_b_metadata.get("latency_seconds")),
        }
        rows.extend(
            (
                _result_row(
                    case_id=case.id,
                    strategy="baseline",
                    candidate="baseline",
                    scores=baseline_scores,
                    metadata=baseline_metadata,
                    summary=_summary_text(evaluation.data, "baseline"),
                ),
                _result_row(
                    case_id=case.id,
                    strategy="structured",
                    candidate="structured_a",
                    scores=structured_a_scores,
                    metadata=structured_a_metadata,
                    summary=_summary_text(evaluation.data, "structured_a"),
                ),
                _result_row(
                    case_id=case.id,
                    strategy="best_of_two",
                    candidate=selected,
                    scores=selected_scores,
                    metadata=combined_generation_metadata,
                    extra_metadata=selection_metadata,
                    summary=selected_summary,
                ),
            )
        )
        (case_root / "evaluation.json").write_text(
            json.dumps(
                {
                    "attributes": attributes,
                    "evaluation": evaluation.data,
                    "selected": selected,
                    "selection_cost_usd": (
                        str(evaluation.cost_usd) if evaluation.cost_usd is not None else None
                    ),
                    "selection_latency_seconds": evaluation.latency_seconds,
                    "best_of_two_image": str(_image_path(best_dir)),
                },
                indent=2,
            )
            + "\n"
        )

    _write_csv(output_root / "results.csv", rows)
    _write_csv(output_root / "manual_scores.csv", _manual_rows(rows))
    strategy_means = _strategy_means(rows)
    auto_winner = max(strategy_means, key=strategy_means.__getitem__)
    (output_root / "development_summary.json").write_text(
        json.dumps(
            {
                "auto_strategy_means": strategy_means,
                "auto_winner": auto_winner,
                "attribute_extraction_cost_usd": str(attribute_cost),
                "attribute_extraction_latency_seconds": attribute_latency,
                "development_cases": list(DEVELOPMENT_CASE_IDS),
                "evaluator_model": evaluator_model,
                "generator_model": generator_model,
                "holdout_calls": 0,
                "image_requests": 9,
                "vlm_requests": 6,
                "total_generation_cost_usd": str(actual_generation_cost),
                "total_generation_latency_seconds": actual_generation_latency,
                "total_selection_cost_usd": str(actual_selection_cost),
                "total_selection_latency_seconds": actual_selection_latency,
                "winner_status": "pending manual sanity check",
            },
            indent=2,
        )
        + "\n"
    )
    return output_root
