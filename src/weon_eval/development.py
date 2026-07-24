"""Run the complete D01-D03 development experiment matrix."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from weon_eval.cases import Case, load_cases
from weon_eval.evaluation import (
    JsonRequester,
    attribute_schema,
    choose_best,
    evaluation_schema,
    parse_attributes,
    parse_scores,
    summary_text,
    validate_applicability_masks,
)
from weon_eval.prompts import render_prompt, render_structured_prompt
from weon_eval.reporting import (
    decimal_value,
    float_value,
    image_path,
    manual_rows,
    metadata,
    result_row,
    strategy_means,
    write_best_of_two,
    write_contact_sheet,
    write_csv,
)
from weon_eval.runner import Generator, run_case
from weon_eval.vlm import request_json

DEVELOPMENT_CASE_IDS = ("D01", "D02", "D03")
DEFAULT_GENERATOR_MODEL = "google/gemini-3.1-flash-lite-image"
DEFAULT_EVALUATOR_MODEL = "openai/gpt-4.1-mini"


def _development_cases(cases_path: Path) -> list[Case]:
    cases = load_cases(cases_path)
    selected: list[Case] = []
    for case_id in DEVELOPMENT_CASE_IDS:
        case = cases[case_id]
        if case.split != "development":
            raise ValueError(f"{case_id} is not a development case")
        selected.append(case)
    return selected


def _attribute_prompt() -> str:
    return (
        "Inspect only the garment packshot image(s). Describe the visible garment facts "
        "for the requested dimensions. Use 'not visible' when a detail cannot be seen; "
        "do not infer hidden details."
    )


def _evaluation_prompt() -> str:
    return (
        "Image order: garment packshot, baseline result, structured candidate A, "
        "structured candidate B. Score each result against the garment packshot on "
        "color, print/logo, silhouette/length, construction details, texture/material, "
        "and garment presence. Use 1 for preserved, 0.5 for partial, 0 for drifted, "
        "and -1 only when the source attribute is genuinely not applicable."
    )


def _write_attributes(
    *,
    path: Path,
    attributes: dict[str, str],
    model: str,
    cost_usd: Decimal | None,
    latency_seconds: float,
) -> None:
    path.write_text(
        json.dumps(
            {
                "attributes": attributes,
                "cost_usd": str(cost_usd) if cost_usd is not None else None,
                "latency_seconds": latency_seconds,
                "model": model,
            },
            indent=2,
        )
        + "\n"
    )


def _write_evaluation(
    *,
    path: Path,
    attributes: dict[str, str],
    evaluation_data: dict[str, object],
    selected: str,
    selection_cost_usd: Decimal | None,
    selection_latency_seconds: float,
    best_image: Path,
) -> None:
    path.write_text(
        json.dumps(
            {
                "attributes": attributes,
                "evaluation": evaluation_data,
                "selected": selected,
                "selection_cost_usd": (
                    str(selection_cost_usd) if selection_cost_usd is not None else None
                ),
                "selection_latency_seconds": selection_latency_seconds,
                "best_of_two_image": str(best_image),
            },
            indent=2,
        )
        + "\n"
    )


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
    selected_cases = _development_cases(cases_path)
    output_root.mkdir(parents=True)

    rows: list[dict[str, object]] = []
    attribute_cost = Decimal("0")
    attribute_latency = 0.0
    generation_cost = Decimal("0")
    generation_latency = 0.0
    selection_cost = Decimal("0")
    selection_latency = 0.0

    for case in selected_cases:
        case_root = output_root / case.id
        case_root.mkdir()
        attribute_result = requester(
            model=evaluator_model,
            prompt=_attribute_prompt(),
            image_paths=case.garments,
            schema_name="garment_attributes",
            schema=attribute_schema(),
            api_key=api_key,
        )
        attributes = parse_attributes(attribute_result.data)
        attribute_cost += attribute_result.cost_usd or Decimal("0")
        attribute_latency += attribute_result.latency_seconds
        _write_attributes(
            path=case_root / "attributes.json",
            attributes=attributes,
            model=evaluator_model,
            cost_usd=attribute_result.cost_usd,
            latency_seconds=attribute_result.latency_seconds,
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

        baseline_image = image_path(baseline_dir)
        structured_a_image = image_path(structured_a_dir)
        structured_b_image = image_path(structured_b_dir)
        evaluation = requester(
            model=evaluator_model,
            prompt=_evaluation_prompt(),
            image_paths=(
                *case.garments,
                baseline_image,
                structured_a_image,
                structured_b_image,
            ),
            schema_name="garment_comparison",
            schema=evaluation_schema(),
            api_key=api_key,
        )
        baseline_scores = parse_scores(evaluation.data, "baseline")
        structured_a_scores = parse_scores(evaluation.data, "structured_a")
        structured_b_scores = parse_scores(evaluation.data, "structured_b")
        validate_applicability_masks(
            baseline_scores,
            structured_a_scores,
            structured_b_scores,
        )
        selected = choose_best(structured_a_scores, structured_b_scores)
        selected_scores = (
            structured_a_scores if selected == "structured_a" else structured_b_scores
        )
        best_dir = write_best_of_two(
            case_root=case_root,
            selected=selected,
            structured_a_dir=structured_a_dir,
            structured_b_dir=structured_b_dir,
            evaluation=evaluation,
        )
        write_contact_sheet(
            garment=case.garments[0],
            baseline=baseline_image,
            structured_a=structured_a_image,
            structured_b=structured_b_image,
            selected=selected,
            output=case_root / "contact_sheet.jpg",
        )

        baseline_metadata = metadata(baseline_dir)
        structured_a_metadata = metadata(structured_a_dir)
        structured_b_metadata = metadata(structured_b_dir)
        for unique_metadata in (
            baseline_metadata,
            structured_a_metadata,
            structured_b_metadata,
        ):
            generation_cost += decimal_value(unique_metadata.get("cost_usd"))
            generation_latency += float_value(unique_metadata.get("latency_seconds"))
        selection_cost += evaluation.cost_usd or Decimal("0")
        selection_latency += evaluation.latency_seconds

        attribute_metadata: dict[str, object] = {
            "cost_usd": (
                str(attribute_result.cost_usd)
                if attribute_result.cost_usd is not None
                else None
            ),
            "latency_seconds": attribute_result.latency_seconds,
        }
        selection_metadata: dict[str, object] = {
            "selection_cost_usd": (
                str(evaluation.cost_usd) if evaluation.cost_usd is not None else None
            ),
            "selection_latency_seconds": evaluation.latency_seconds,
        }
        combined_metadata: dict[str, object] = {
            "cost_usd": str(
                decimal_value(structured_a_metadata.get("cost_usd"))
                + decimal_value(structured_b_metadata.get("cost_usd"))
            ),
            "latency_seconds": float_value(
                structured_a_metadata.get("latency_seconds")
            )
            + float_value(structured_b_metadata.get("latency_seconds")),
        }
        rows.extend(
            (
                result_row(
                    case_id=case.id,
                    strategy="baseline",
                    candidate="baseline",
                    scores=baseline_scores,
                    run_metadata=baseline_metadata,
                    summary=summary_text(evaluation.data, "baseline"),
                ),
                result_row(
                    case_id=case.id,
                    strategy="structured",
                    candidate="structured_a",
                    scores=structured_a_scores,
                    run_metadata=structured_a_metadata,
                    attribute_metadata=attribute_metadata,
                    summary=summary_text(evaluation.data, "structured_a"),
                ),
                result_row(
                    case_id=case.id,
                    strategy="best_of_two",
                    candidate=selected,
                    scores=selected_scores,
                    run_metadata=combined_metadata,
                    attribute_metadata=attribute_metadata,
                    selection_metadata=selection_metadata,
                    summary=summary_text(evaluation.data, selected),
                ),
            )
        )
        _write_evaluation(
            path=case_root / "evaluation.json",
            attributes=attributes,
            evaluation_data=evaluation.data,
            selected=selected,
            selection_cost_usd=evaluation.cost_usd,
            selection_latency_seconds=evaluation.latency_seconds,
            best_image=image_path(best_dir),
        )

    write_csv(output_root / "results.csv", rows)
    write_csv(output_root / "manual_scores.csv", manual_rows(rows))
    auto_strategy_means = strategy_means(rows)
    auto_winner = max(auto_strategy_means, key=auto_strategy_means.__getitem__)
    (output_root / "development_summary.json").write_text(
        json.dumps(
            {
                "auto_strategy_means": auto_strategy_means,
                "auto_winner": auto_winner,
                "attribute_extraction_cost_usd": str(attribute_cost),
                "attribute_extraction_latency_seconds": attribute_latency,
                "development_cases": list(DEVELOPMENT_CASE_IDS),
                "evaluator_model": evaluator_model,
                "generator_model": generator_model,
                "holdout_calls": 0,
                "image_requests": 9,
                "vlm_requests": 6,
                "total_generation_cost_usd": str(generation_cost),
                "total_generation_latency_seconds": generation_latency,
                "total_selection_cost_usd": str(selection_cost),
                "total_selection_latency_seconds": selection_latency,
                "winner_status": "pending manual sanity check",
            },
            indent=2,
        )
        + "\n"
    )
    return output_root
