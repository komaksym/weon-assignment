"""Promote the top two targeted methods through fixed best-of-two and repair pipelines."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
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
    TARGETED_METHODS,
    SearchMethod,
    build_payload,
    method_prompt,
    method_reference_paths,
)
from weon_eval.vlm import JsonResult, VlmError, request_json

DEVELOPMENT_CASE_IDS = ("D01", "D02", "D03")
DEFAULT_PROMOTION_FLOOR_USD = Decimal("0.30")
DEFAULT_MAX_PAID_REQUESTS = 300
VLM_RESERVE_USD = Decimal("0.02")
SELECTOR_MODEL = "openai/gpt-4.1-mini"
SELECTOR_PROMPT = (
    "Image order: garment packshot(s), candidate_1, candidate_2. Candidate IDs are opaque. "
    "Choose the candidate that better preserves the exact source garment across color, "
    "print/logo, silhouette/length, construction details, texture/material, and presence. "
    "Ignore general aesthetics, person attractiveness, pose, and background quality. "
    "If garment fidelity is indistinguishable, set tie=true and winner=candidate_1."
)

Generator = Callable[[dict[str, object], str], GenerationResult]
AllowanceGetter = Callable[[str], KeyAllowance]
Clock = Callable[[], float]


@dataclass(frozen=True)
class PromotionMethod:
    """One fixed promotion pipeline around a selected stage-one method."""

    name: str
    base_method: SearchMethod
    mode: str


@dataclass(frozen=True)
class GeneratedCandidate:
    """One generated candidate and its measurements."""

    label: str
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
        if self.count >= maximum:
            raise RequestCapReached("paid request cap reached")
        self.count += 1


class FloorReached(RuntimeError):
    """Raised when a full promotion sample cannot preserve the floor."""


class RequestCapReached(RuntimeError):
    """Raised when the next paid call would exceed the cap."""


def _targeted(name: str) -> SearchMethod:
    return next(method for method in TARGETED_METHODS if method.name == name)


PROMOTION_METHODS = (
    PromotionMethod(
        "duplicate_garment_best_of_two",
        _targeted("lite_duplicate_garment"),
        "best_of_two",
    ),
    PromotionMethod(
        "identity_tight_crop_best_of_two",
        _targeted("lite_identity_tight_crop"),
        "best_of_two",
    ),
    PromotionMethod(
        "duplicate_garment_repair",
        _targeted("lite_duplicate_garment"),
        "repair",
    ),
    PromotionMethod(
        "identity_tight_crop_repair",
        _targeted("lite_identity_tight_crop"),
        "repair",
    ),
)


def selector_schema() -> dict[str, object]:
    """Return the fixed opaque two-candidate selection schema."""

    return {
        "type": "object",
        "properties": {
            "winner": {"type": "string", "enum": ["candidate_1", "candidate_2"]},
            "tie": {"type": "boolean"},
            "summary": {"type": "string", "minLength": 1},
        },
        "required": ["winner", "tie", "summary"],
        "additionalProperties": False,
    }


def selector_mapping(method_name: str, case_id: str, replicate: int) -> dict[str, str]:
    """Return a deterministic opaque mapping from candidate IDs to A/B."""

    digest = hashlib.sha256(f"{method_name}:{case_id}:{replicate}".encode()).digest()
    if digest[0] % 2 == 0:
        return {"candidate_1": "a", "candidate_2": "b"}
    return {"candidate_1": "b", "candidate_2": "a"}


def parse_selector(data: Mapping[str, object]) -> tuple[str, bool, str]:
    """Validate one selector result."""

    winner = data.get("winner")
    tie = data.get("tie")
    summary = data.get("summary")
    if winner not in {"candidate_1", "candidate_2"}:
        raise ValueError("selector returned an invalid winner")
    if not isinstance(tie, bool):
        raise ValueError("selector returned an invalid tie flag")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("selector returned no summary")
    if tie and winner != "candidate_1":
        raise ValueError("selector ties must resolve to candidate_1")
    return str(winner), tie, summary.strip()


def _decimal_cost(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0")


def _extension(media_type: str) -> str:
    extensions = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    try:
        return extensions[media_type]
    except KeyError as exc:
        raise ValueError(f"unsupported generated media type: {media_type}") from exc


def _write_rows(path: Path, rows: Sequence[dict[str, object]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _development_cases(cases_path: Path) -> tuple[Case, ...]:
    cases = load_cases(cases_path)
    selected = tuple(cases[case_id] for case_id in DEVELOPMENT_CASE_IDS)
    if any(case.split != "development" for case in selected):
        raise ValueError("promotion search can access development cases only")
    return selected


def _generate(
    *,
    label: str,
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
) -> GeneratedCandidate:
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
    latency_seconds = clock() - started_at
    after = allowance_getter(api_key)
    if after.remaining_usd < floor_usd:
        raise BudgetError("generation crossed the configured allowance floor")

    output_dir.mkdir(parents=True, exist_ok=False)
    image_path = output_dir / f"image{_extension(result.media_type)}"
    image_path.write_bytes(result.image)
    cost = _decimal_cost(result.cost_usd)
    metadata = {
        "label": label,
        "model": model,
        "prompt": prompt,
        "references": reference_metadata,
        "cost_usd": str(cost),
        "latency_seconds": latency_seconds,
        "balance_before_usd": str(before.remaining_usd),
        "balance_after_usd": str(after.remaining_usd),
        "output_media_type": result.media_type,
        "image_file": image_path.name,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return GeneratedCandidate(
        label=label,
        image_path=image_path,
        cost_usd=cost,
        latency_seconds=latency_seconds,
        balance_before_usd=before.remaining_usd,
        balance_after_usd=after.remaining_usd,
    )


def _select_best_of_two(
    *,
    method_name: str,
    case: Case,
    replicate: int,
    candidate_a: GeneratedCandidate,
    candidate_b: GeneratedCandidate,
    raw_output_path: Path,
    api_key: str,
    requester: JsonRequester,
    allowance_getter: AllowanceGetter,
    request_counter: PaidRequestCounter,
    max_paid_requests: int,
    floor_usd: Decimal,
) -> tuple[GeneratedCandidate, JsonResult, bool, str, dict[str, str]]:
    before = allowance_getter(api_key)
    if not can_spend(before, VLM_RESERVE_USD, floor_usd):
        raise FloorReached("selector reserve would cross the allowance floor")
    mapping = selector_mapping(method_name, case.id, replicate)
    candidates = {"a": candidate_a, "b": candidate_b}
    image_paths = (
        *case.garments,
        candidates[mapping["candidate_1"]].image_path,
        candidates[mapping["candidate_2"]].image_path,
    )
    request_counter.consume(max_paid_requests)
    result = requester(
        model=SELECTOR_MODEL,
        prompt=SELECTOR_PROMPT,
        image_paths=image_paths,
        schema_name="promotion_selector",
        schema=selector_schema(),
        api_key=api_key,
    )
    after = allowance_getter(api_key)
    if after.remaining_usd < floor_usd:
        raise BudgetError("selector crossed the configured allowance floor")
    winner_id, tie, summary = parse_selector(result.data)
    selected = candidates[mapping[winner_id]]
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_output = {
        "selector_model": SELECTOR_MODEL,
        "prompt": SELECTOR_PROMPT,
        "opaque_mapping": mapping,
        "selector": result.data,
        "selected_label": selected.label,
        "cost_usd": str(result.cost_usd) if result.cost_usd is not None else None,
        "latency_seconds": result.latency_seconds,
        "balance_before_usd": str(before.remaining_usd),
        "balance_after_usd": str(after.remaining_usd),
    }
    raw_output_path.write_text(json.dumps(raw_output, indent=2) + "\n")
    return selected, result, tie, summary, mapping


def _run_promotion_case(
    *,
    method: PromotionMethod,
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
    reference_paths = method_reference_paths(case, method.base_method, work_dir)
    prompt = method_prompt(method.base_method, baseline_prompt)

    first = _generate(
        label="a",
        model=method.base_method.model,
        prompt=prompt,
        reference_paths=reference_paths,
        reserve_usd=method.base_method.generation_reserve_usd,
        floor_usd=floor_usd,
        output_dir=case_root / "candidate-a",
        api_key=api_key,
        generator=generator,
        allowance_getter=allowance_getter,
        request_counter=request_counter,
        max_paid_requests=max_paid_requests,
        clock=clock,
    )
    generations = [first]
    selected = first
    selector_result: JsonResult | None = None
    selector_tie: bool | None = None
    selector_summary = ""
    selector_map: dict[str, str] = {}

    if method.mode == "best_of_two":
        second = _generate(
            label="b",
            model=method.base_method.model,
            prompt=prompt,
            reference_paths=reference_paths,
            reserve_usd=method.base_method.generation_reserve_usd,
            floor_usd=floor_usd,
            output_dir=case_root / "candidate-b",
            api_key=api_key,
            generator=generator,
            allowance_getter=allowance_getter,
            request_counter=request_counter,
            max_paid_requests=max_paid_requests,
            clock=clock,
        )
        generations.append(second)
        selected, selector_result, selector_tie, selector_summary, selector_map = (
            _select_best_of_two(
                method_name=method.name,
                case=case,
                replicate=replicate,
                candidate_a=first,
                candidate_b=second,
                raw_output_path=case_root / "selector.json",
                api_key=api_key,
                requester=requester,
                allowance_getter=allowance_getter,
                request_counter=request_counter,
                max_paid_requests=max_paid_requests,
                floor_usd=floor_usd,
            )
        )
    elif method.mode == "repair":
        repaired = _generate(
            label="repair",
            model=method.base_method.model,
            prompt=REPAIR_PROMPT,
            reference_paths=(first.image_path, *case.garments),
            reserve_usd=method.base_method.generation_reserve_usd,
            floor_usd=floor_usd,
            output_dir=case_root / "repair",
            api_key=api_key,
            generator=generator,
            allowance_getter=allowance_getter,
            request_counter=request_counter,
            max_paid_requests=max_paid_requests,
            clock=clock,
        )
        generations.append(repaired)
        selected = repaired
    else:
        raise ValueError(f"unsupported promotion mode: {method.mode}")

    evaluation_before = allowance_getter(api_key)
    if not can_spend(evaluation_before, VLM_RESERVE_USD, floor_usd):
        raise FloorReached("evaluation reserve would cross the allowance floor")
    request_counter.consume(max_paid_requests)
    score = score_candidate(
        case_id=case.id,
        garment_paths=case.garments,
        candidate_path=selected.image_path,
        raw_output_path=case_root / "evaluation.json",
        api_key=api_key,
        evaluator_model=DEFAULT_EVALUATOR_MODEL,
        requester=requester,
    )
    evaluation_after = allowance_getter(api_key)
    if evaluation_after.remaining_usd < floor_usd:
        raise BudgetError("evaluation crossed the configured allowance floor")

    generation_cost = sum((item.cost_usd for item in generations), Decimal("0"))
    generation_latency = sum(item.latency_seconds for item in generations)
    selector_cost = _decimal_cost(selector_result.cost_usd) if selector_result else Decimal("0")
    selector_latency = selector_result.latency_seconds if selector_result else 0.0
    evaluation_cost = _decimal_cost(score.cost_usd)
    row: dict[str, object] = {
        "method": method.name,
        "base_method": method.base_method.name,
        "promotion_mode": method.mode,
        "case_id": case.id,
        "replicate": replicate,
        "model": method.base_method.model,
        "selected_label": selected.label,
        "selector_tie": selector_tie if selector_tie is not None else "",
        "selector_summary": selector_summary,
        "selector_mapping": json.dumps(selector_map, sort_keys=True) if selector_map else "",
        "mean_auto_score": score.mean,
        "generation_cost_usd": str(generation_cost),
        "selector_cost_usd": str(selector_cost),
        "evaluation_cost_usd": str(evaluation_cost),
        "total_cost_usd": str(generation_cost + selector_cost + evaluation_cost),
        "generation_latency_seconds": generation_latency,
        "selector_latency_seconds": selector_latency,
        "evaluation_latency_seconds": score.latency_seconds,
        "total_latency_seconds": generation_latency + selector_latency + score.latency_seconds,
        "balance_before_usd": str(generations[0].balance_before_usd),
        "balance_after_usd": str(evaluation_after.remaining_usd),
        "candidate_path": str(selected.image_path),
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
    for method_name, method_rows in grouped.items():
        dimension_means: dict[str, float] = {}
        for dimension in ATTRIBUTE_DIMENSIONS:
            values = [
                float_value(row[dimension])
                for row in method_rows
                if float_value(row[dimension]) >= 0
            ]
            dimension_means[dimension] = _mean(values) if values else -1.0
        identity_values = [
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
            "method": method_name,
            "base_method": method_rows[0]["base_method"],
            "promotion_mode": method_rows[0]["promotion_mode"],
            "valid_samples": len(method_rows),
            "mean_auto_score": _mean(
                [float_value(row["mean_auto_score"]) for row in method_rows]
            ),
            "identity_detail_mean": _mean(identity_values),
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


def _method_reserve(method: PromotionMethod) -> tuple[int, Decimal]:
    required_requests = 4 if method.mode == "best_of_two" else 3
    combined_reserve = (
        method.base_method.generation_reserve_usd * 2
        + VLM_RESERVE_USD
        + (VLM_RESERVE_USD if method.mode == "best_of_two" else Decimal("0"))
    )
    return required_requests, combined_reserve


def run_promotion_search(
    *,
    cases_path: Path,
    prompt_path: Path,
    api_key: str,
    output_root: Path,
    floor_usd: Decimal = DEFAULT_PROMOTION_FLOOR_USD,
    max_paid_requests: int = DEFAULT_MAX_PAID_REQUESTS,
    methods: Sequence[PromotionMethod] = PROMOTION_METHODS,
    generator: Generator = generate_image,
    requester: JsonRequester = request_json,
    allowance_getter: AllowanceGetter = get_key_allowance,
    clock: Clock = monotonic,
) -> Path:
    """Run fixed top-two promotion pipelines until the floor or request cap."""

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
    counter = PaidRequestCounter()
    replicate = 1
    stop_reason = "request_cap"

    while counter.count < max_paid_requests:
        successful_this_round = 0
        attempted_this_round = 0
        for method in methods:
            required_requests, combined_reserve = _method_reserve(method)
            full_case_requests = required_requests * len(cases)
            full_case_reserve = combined_reserve * len(cases)
            current = allowance_getter(api_key)
            if counter.count + full_case_requests > max_paid_requests:
                stop_reason = "request_cap"
                break
            if not can_spend(current, full_case_reserve, floor_usd):
                skips.append(
                    {
                        "method": method.name,
                        "replicate": replicate,
                        "reason": "full D01-D03 reserve would cross floor",
                        "remaining_usd": str(current.remaining_usd),
                        "full_case_reserve_usd": str(full_case_reserve),
                    }
                )
                continue

            for case in cases:
                attempted_this_round += 1
                try:
                    row = _run_promotion_case(
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
                        request_counter=counter,
                        max_paid_requests=max_paid_requests,
                        clock=clock,
                    )
                except FloorReached:
                    stop_reason = "floor_guard"
                    continue
                except RequestCapReached:
                    stop_reason = "request_cap"
                    break
                except (GenerationError, VlmError, ValueError, BudgetError) as exc:
                    failures.append(
                        {
                            "method": method.name,
                            "case_id": case.id,
                            "replicate": replicate,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "remaining_usd": str(allowance_getter(api_key).remaining_usd),
                            "paid_requests_so_far": counter.count,
                        }
                    )
                    continue
                rows.append(row)
                successful_this_round += 1
            if stop_reason == "request_cap" and counter.count >= max_paid_requests:
                break

        if successful_this_round == 0:
            if stop_reason != "request_cap":
                stop_reason = (
                    "floor_guard" if attempted_this_round == 0 else "no_successful_candidates"
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
    summary = {
        "starting_allowance_usd": str(starting.remaining_usd),
        "ending_allowance_usd": str(ending.remaining_usd),
        "floor_usd": str(floor_usd),
        "spent_usd": str(starting.remaining_usd - ending.remaining_usd),
        "paid_requests": counter.count,
        "successful_candidates": len(rows),
        "failure_count": len(failures),
        "skip_count": len(skips),
        "replicates_started": replicate,
        "stop_reason": stop_reason,
        "winner": winner,
        "promoted_stage_one_methods": [
            "lite_duplicate_garment",
            "lite_identity_tight_crop",
        ],
        "promotion_methods": [method.name for method in methods],
        "selector_model": SELECTOR_MODEL,
        "selector_prompt_frozen": True,
        "evaluator_model": DEFAULT_EVALUATOR_MODEL,
        "evaluation_prompt_frozen": True,
        "complete_case_blocks_required": True,
        "holdout_requests": 0,
        "automatic_retries": 0,
    }
    (output_root / "search_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return output_root
