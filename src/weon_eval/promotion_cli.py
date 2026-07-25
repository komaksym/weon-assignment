"""CLI for the fixed top-two promotion search."""

from __future__ import annotations

import argparse
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path

from weon_eval.promotion_search import (
    DEFAULT_MAX_PAID_REQUESTS,
    DEFAULT_PROMOTION_FLOOR_USD,
    run_promotion_search,
)


def _decimal(value: str) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("must be a decimal number") from exc
    if result < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path("cases.json"))
    parser.add_argument("--prompt", type=Path, default=Path("prompts/baseline.txt"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/promotion-search"),
    )
    parser.add_argument(
        "--floor-usd",
        type=_decimal,
        default=DEFAULT_PROMOTION_FLOOR_USD,
    )
    parser.add_argument(
        "--max-paid-requests",
        type=int,
        default=DEFAULT_MAX_PAID_REQUESTS,
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is not configured")
    run_promotion_search(
        cases_path=args.cases,
        prompt_path=args.prompt,
        api_key=api_key,
        output_root=args.output,
        floor_usd=args.floor_usd,
        max_paid_requests=args.max_paid_requests,
    )


if __name__ == "__main__":
    main()
