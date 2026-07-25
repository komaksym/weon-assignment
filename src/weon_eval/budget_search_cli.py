"""CLI for the balance-guarded garment-consistency search."""

from __future__ import annotations

import argparse
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path

from weon_eval.budget_search import (
    DEFAULT_FLOOR_USD,
    DEFAULT_MAX_PAID_REQUESTS,
    run_budget_search,
)
from weon_eval.search_methods import METHOD_SETS, SEARCH_METHODS, SearchMethod


def _decimal(value: str) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("must be a decimal number") from exc
    if result < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return result


def execution_methods(method_set: str) -> tuple[SearchMethod, ...]:
    """Return one frozen method queue, including a same-run targeted control."""

    methods = METHOD_SETS[method_set]
    if method_set == "targeted":
        return (SEARCH_METHODS[0], *methods)
    return methods


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path("cases.json"))
    parser.add_argument("--prompt", type=Path, default=Path("prompts/baseline.txt"))
    parser.add_argument("--output", type=Path, default=Path("outputs/budget-search"))
    parser.add_argument("--floor-usd", type=_decimal, default=DEFAULT_FLOOR_USD)
    parser.add_argument(
        "--max-paid-requests",
        type=int,
        default=DEFAULT_MAX_PAID_REQUESTS,
    )
    parser.add_argument(
        "--method-set",
        choices=tuple(METHOD_SETS),
        default="broad",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is not configured")
    run_budget_search(
        cases_path=args.cases,
        prompt_path=args.prompt,
        api_key=api_key,
        output_root=args.output,
        floor_usd=args.floor_usd,
        max_paid_requests=args.max_paid_requests,
        methods=execution_methods(args.method_set),
    )


if __name__ == "__main__":
    main()
