"""Run a frozen-evaluation method search down to a key allowance floor."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from time import monotonic

from weon_eval.budget import BudgetError, KeyAllowance, can_spend, get_key_allowance
from weon_eval.cases import Case, load_cases
from weon_eval.evaluation import JsonRequester
from weon_eval.frozen_scoring import DEFAULT_EVALUATOR_MODEL, score_candidate
from weon_eval.openrouter import GenerationError, GenerationResult, generate_image
from weon_eval.prompts import ATTRIBUTE_DIMENSIONS, render_prompt
from weon_eval.reporting import float_value
from weon_eval.search_methods import (
    REPAIR_PROMPT,
    SEARCH_METHODS,
    SearchMethod,
    build_payload,
    method_prompt,
    method_reference_paths,
)
from weon_eval.vlm import VlmError, request_json

DEVELOPMENT_CASE_IDS = ("D01", "D02", "D03")
DEFAULT_FLOOR_USD = Decimal("10.00")
EVALUATION_RESERVE_USD = Decimal("0.02")
NEAR_FLOOR_WINDOW_USD = Decimal("0.50")
DEFAULT_MAX_PAID_REQUESTS = 300
Generator = Callable[[dict[str, object], str], GenerationResult]
AllowanceGetter = Callable[[str], KeyAllowance]
Clock = Callable[[], float]


@dataclass(frozen=True)
class GenerationEvidence:
    """One successful generation call and its balance snapshots."""

    image_path: Path
    cost_usd: Decimal
    latency_seconds: float
    balance_before_usd: Decimal
    balance_after_usd: Decimal


@dataclass
class PaidRequestCounter:
    """Count every attempted paid network call, including failures."""

    count: int = 0

    def consume(self, maximum: int) -> None:
        """Reserve one paid-call slot before the network request starts."""

        if self.count >= maximum:
            raise RequestCapReached("paid request cap reached")
        self.count += 1


class RequestCapReached(RuntimeError):
    """Raised when the next paid call would exceed the request cap."""


class FloorReached(RuntimeError):
    """Raised when the next paid call cannot preserve the allowance floor."""


def _development_cases(cases_path: Path) -> tuple[Case, ...]:
    cases = load_cases(cases_path)
    selected: list[Case] = []
    for case_id in DEVELOPMENT_CASE_IDS:
        case = cases[case_id]
        if case.split != "development":
            raise ValueError(f"{case_id} is not a development case")
        selected.append(case)
    return tuple(selected)


def _extension(media_type: str) -> str:
    extensions = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    try:
        return extensions[media_type]
    except KeyError as exc:
        raise ValueError(f"unsupported generated media type: {media_type}") from exc


def _decimal_cost(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0")


def _write_rows(path: Path, rows: Sequence[dict[str, object]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _generate(
    *,
    model: str,
    prompt: str,
    reference_paths: tuple[Path, ...],
    reserve_usd: Decimal,
    floor_usd: Decimal,
    output_dir: Path,
    api_key: str,
    generator: Generator,
    allowance_getter: AllowanceGetter,
    request_counter: PaidRequestCounter,
    max_paid_requests: int,
    clock: Clock,
) -> GenerationEvidence:
    before = allowance_getter(api_key)
    if not can_spend(before, reserve_usd, floor_usd):
        raise FloorReached("generation reserve would cross the allowance floor")
    payload, reference_metadata = build_payload(
        model=model,
        prompt=prompt,
        reference_paths=reference_paths,
    )
    request_counter.consume(max_paid_requests)
    started_at = clock()
    result = generator(payload, api_key)
    latency = clock() - started_at
    after = allowance_getter(api_key)
    if after.remaining_usd < floor_usd:
        raise BudgetError("generation crossed the configured allowance floor")

    output_dir.mkdir(parents=True, exist_ok=False)
    image_path = output_dir / f"image{_extension(result.media_type)}"
    image_path.write_bytes(result.image)
    cost = _decimal_cost(result.cost_usd)
    (output_dir / "metadata.json").write_text(
        json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "references": reference_metadata,
                "cost_usd": str(cost),
                "latency_seconds": latency,
                "balance_before_usd": str(before.remaining_usd),
                "balance_after_usd": str(after.remaining_usd),
                "output_media_type": result.media_type,
                "image_file": image_path.name,
            },
            indent=2,
        )
        + "\n"
    )
    return GenerationEvidence(
        image_path=image_path,
        cost_usd=cost,
        latency_seconds=latency,
        balance_before_usd=before.remaining_usd,
        balance_after_usd=after.remaining_usd,
    )


def _run_method_case(
    *,
    method: SearchMethod,
    case: Case,
    replicate: int,
    baseline_prompt: str,
    output_root: Path,
    api_key: str,
    floor_usd: Decimal,
    generator: Generator,
    requester: JsonRequester,
    allowance_getter: AllowanceGetter,
    request_counter: PaidRequestCounter,
    max_paid_requests: int,
    clock: Clock,
) -> dict[str, object]:
    case_root = output_root / f"replicate-{replicate:03d}" / method.name / case.id
    work_dir = case_root / "work"
    reference_paths = method_reference_paths(case, method, work_dir)
    prompt = method_prompt(method, baseline_prompt)
    generations: list[GenerationEvidence] = []

    first = _generate(
        model=method.model,
        prompt=prompt,
        reference_paths=reference_paths,
        reserve_usd=method.generation_reserve_usd,
        floor_usd=floor_usd,
        output_dir=case_root / "pass-1",
        api_key=api_key,
        generator=generator,
        allowance_getter=allowance_getter,
        request_counter=request_counter,
        max_paid_requests=max_paid_requests,
        clock=clock,
    )
    generations.append(first)
    final_image = first.image_path

    if method.passes == 2:
        second = _generate(
            model=method.model,
            prompt=REPAIR_PROMPT,
            reference_paths=(first.image_path, *case.garments),
            reserve_usd=method.generation_reserve_usd,
            floor_usd=floor_usd,
            output_dir=case_root / "pass-2",
            api_key=api_key,
            generator=generator,
            allowance_getter=allowance_getter,
            request_counter=request_counter,
            max_paid_requests=max_paid_requests,
            clock=clock,
        )
        generations.append(second)
        final_image = second.image_path

    evaluation_before = allowance_getter(api_key)
    if not can_spend(evaluation_before, EVALUATION_RESERVE_USD, floor_usd):
        raise FloorReached("evaluation reserve would cross the allowance floor")
    raw_evaluation = case_root / "evaluation.json"
    request_counter.consume(max_paid_requests)
    score = score_candidate(
        case_id=case.id,
        garment_paths=case.garments,
        candidate_path=final_image,
        raw_output_path=raw_evaluation,
        api_key=api_key,
        evaluator_model=DEFAULT_EVALUATOR_MODEL,
        requester=requester,
    )
    evaluation_after = allowance_getter(api_key)
    if evaluation_after.remaining_usd < floor_usd:
        raise BudgetError("evaluation crossed the configured allowance floor")

    generation_cost = sum((item.cost_usd for item in generations), Decimal("0"))
    generation_latency = sum(item.latency_seconds for item in generations)
    row: dict[str, object] = {
        "method": method.name,
        "case_id": case.id,
        "replicate": replicate,
        "model": method.model,
        "passes": method.passes,
        "mean_auto_score": score.mean,
        "valid": True,
        "generation_cost_usd": str(generation_cost),
        "evaluation_cost_usd": str(_decimal_cost(score.cost_usd)),
        "total_cost_usd": str(generation_cost + _decimal_cost(score.cost_usd)),
        "generation_latency_seconds": generation_latency,
        "evaluation_latency_seconds": score.latency_seconds,
        "total_latency_seconds": generation_latency + score.latency_seconds,
        "balance_before_usd": str(generations[0].balance_before_usd),
        "balance_after_usd": str(evaluation_after.remaining_usd),
        "candidate_path": str(final_image),
        "auto_summary": score.summary,
    }
    row.update(score.scores)
    return row


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _method_summaries(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["method"])].append(row)

    summaries: list[dict[str, object]] = []
    for method, method_rows in grouped.items():
        dimension_means: dict[str, float] = {}
        for dimension in ATTRIBUTE_DIMENSIONS:
            values = [
                float_value(row[dimension])
                for row in method_rows
                if float_value(row[dimension]) >= 0
            ]
            dimension_means[dimension] = _mean(values) if values else -1.0
        detail_values = [
            dimension_means[dimension]
            for dimension in ("print_logo", "construction_details", "texture_material")
            if dimension_means[dimension] >= 0
        ]
        total_cost = sum(
            (Decimal(str(row["total_cost_usd"])) for row in method_rows),
            Decimal("0"),
        )
        total_latency = sum(
            float_value(row["total_latency_seconds"]) for row in method_rows
        )
        summary: dict[str, object] = {
            "method": method,
            "valid_samples": len(method_rows),
            "mean_auto_score": _mean(
                [float_value(row["mean_auto_score"]) for row in method_rows]
            ),
            "identity_detail_mean": _mean(detail_values),
            "total_cost_usd": str(total_cost),
            "average_cost_usd": str(total_cost / len(method_rows)),
            "average_latency_seconds": total_latency / len(method_rows),
        }
        summary.update({f"mean_{key}": value for key, value in dimension_means.items()})
        summaries.append(summary)
    summaries.sort(
        key=lambda row: (
            -float_value(row["mean_auto_score"]),
            -float_value(row["identity_detail_mean"]),
            Decimal(str(row["average_cost_usd"])),
            float_value(row["average_latency_seconds"]),
            str(row["method"]),
        )
    )
    return summaries


def _review_rows(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "method": row["method"],
            "case_id": row["case_id"],
            "replicate": row["replicate"],
            "reviewer": "",
            "review_method": "",
            **{dimension: "" for dimension in ATTRIBUTE_DIMENSIONS},
            "mean_review_score": "",
            "notes": "",
        }
        for row in rows
    ]


def _failure_row(
    *,
    method: SearchMethod,
    case: Case,
    replicate: int,
    error: Exception,
    allowance_getter: AllowanceGetter,
    api_key: str,
    paid_requests: int,
) -> dict[str, object]:
    return {
        "method": method.name,
        "case_id": case.id,
        "replicate": replicate,
        "error_type": type(error).__name__,
        "error": str(error),
        "remaining_usd": str(allowance_getter(api_key).remaining_usd),
        "paid_requests_so_far": paid_requests,
    }


def run_budget_search(
    *,
    cases_path: Path,
    prompt_path: Path,
    api_key: str,
    output_root: Path,
    floor_usd: Decimal = DEFAULT_FLOOR_USD,
    max_paid_requests: int = DEFAULT_MAX_PAID_REQUESTS,
    methods: Sequence[SearchMethod] = SEARCH_METHODS,
    generator: Generator = generate_image,
    requester: JsonRequester = request_json,
    allowance_getter: AllowanceGetter = get_key_allowance,
    clock: Clock = monotonic,
) -> Path:
    """Run predeclared methods round-robin until the floor or request cap stops the search."""

    if output_root.exists():
        raise FileExistsError(f"output already exists: {output_root}")
    if max_paid_requests < 1:
        raise ValueError("max_paid_requests must be positive")
    cases = _development_cases(cases_path)
    baseline_prompts = {case.id: render_prompt(case, prompt_path) for case in cases}
    output_root.mkdir(parents=True)

    starting = allowance_getter(api_key)
    rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    skips: list[dict[str, object]] = []
    disabled_methods: set[str] = set()
    request_counter = PaidRequestCounter()
    replicate = 1
    stop_reason = "request_cap"

    while request_counter.count < max_paid_requests:
        successful_this_round = 0
        eligible_this_round = 0
        request_cap_hit = False
        for method in methods:
            if method.name in disabled_methods:
                continue
            current = allowance_getter(api_key)
            near_floor = current.remaining_usd <= floor_usd + NEAR_FLOOR_WINDOW_USD
            if near_floor and method.name != "lite_direct":
                skips.append(
                    {
                        "method": method.name,
                        "replicate": replicate,
                        "reason": "near-floor descent reserved for lite_direct",
                        "remaining_usd": str(current.remaining_usd),
                    }
                )
                continue
            required_requests = method.passes + 1
            combined_reserve = (
                method.generation_reserve_usd * method.passes
                + EVALUATION_RESERVE_USD
            )
            if request_counter.count + required_requests > max_paid_requests:
                request_cap_hit = True
                break
            if not can_spend(current, combined_reserve, floor_usd):
                skips.append(
                    {
                        "method": method.name,
                        "replicate": replicate,
                        "reason": "combined reserve would cross floor",
                        "remaining_usd": str(current.remaining_usd),
                        "combined_reserve_usd": str(combined_reserve),
                    }
                )
                continue

            for case in cases:
                current = allowance_getter(api_key)
                if request_counter.count + required_requests > max_paid_requests:
                    request_cap_hit = True
                    break
                if not can_spend(current, combined_reserve, floor_usd):
                    skips.append(
                        {
                            "method": method.name,
                            "case_id": case.id,
                            "replicate": replicate,
                            "reason": "combined reserve would cross floor",
                            "remaining_usd": str(current.remaining_usd),
                            "combined_reserve_usd": str(combined_reserve),
                        }
                    )
                    continue
                eligible_this_round += 1
                try:
                    row = _run_method_case(
                        method=method,
                        case=case,
                        replicate=replicate,
                        baseline_prompt=baseline_prompts[case.id],
                        output_root=output_root,
                        api_key=api_key,
                        floor_usd=floor_usd,
                        generator=generator,
                        requester=requester,
                        allowance_getter=allowance_getter,
                        request_counter=request_counter,
                        max_paid_requests=max_paid_requests,
                        clock=clock,
                    )
                except RequestCapReached:
                    request_cap_hit = True
                    break
                except FloorReached:
                    stop_reason = "floor_guard"
                    continue
                except GenerationError as exc:
                    failures.append(
                        _failure_row(
                            method=method,
                            case=case,
                            replicate=replicate,
                            error=exc,
                            allowance_getter=allowance_getter,
                            api_key=api_key,
                            paid_requests=request_counter.count,
                        )
                    )
                    disabled_methods.add(method.name)
                    break
                except (VlmError, ValueError, BudgetError) as exc:
                    failures.append(
                        _failure_row(
                            method=method,
                            case=case,
                            replicate=replicate,
                            error=exc,
                            allowance_getter=allowance_getter,
                            api_key=api_key,
                            paid_requests=request_counter.count,
                        )
                    )
                    continue
                rows.append(row)
                successful_this_round += 1

            if request_cap_hit:
                break

        if request_cap_hit:
            stop_reason = "request_cap"
            break
        if successful_this_round == 0:
            stop_reason = (
                "floor_guard" if eligible_this_round == 0 else "no_successful_candidates"
            )
            break
        replicate += 1

    ending = allowance_getter(api_key)
    summaries = _method_summaries(rows)
    winner = str(summaries[0]["method"]) if summaries else None
    _write_rows(output_root / "results.csv", rows)
    _write_rows(output_root / "method_summary.csv", summaries)
    _write_rows(output_root / "review_scores.csv", _review_rows(rows))
    (output_root / "failures.json").write_text(json.dumps(failures, indent=2) + "\n")
    (output_root / "skips.json").write_text(json.dumps(skips, indent=2) + "\n")
    (output_root / "search_summary.json").write_text(
        json.dumps(
            {
                "starting_allowance_usd": str(starting.remaining_usd),
                "ending_allowance_usd": str(ending.remaining_usd),
                "floor_usd": str(floor_usd),
                "spent_usd": str(starting.remaining_usd - ending.remaining_usd),
                "paid_requests": request_counter.count,
                "successful_candidates": len(rows),
                "failure_count": len(failures),
                "disabled_methods": sorted(disabled_methods),
                "skip_count": len(skips),
                "replicates_started": replicate,
                "stop_reason": stop_reason,
                "winner": winner,
                "evaluator_model": DEFAULT_EVALUATOR_MODEL,
                "evaluation_prompt_frozen": True,
                "holdout_requests": 0,
                "automatic_retries": 0,
            },
            indent=2,
        )
        + "\n"
    )
    return output_root
