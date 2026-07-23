"""Command-line entry point."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from weon_eval.cases import CaseError, load_cases
from weon_eval.openrouter import GenerationError
from weon_eval.prompts import render_prompt
from weon_eval.runner import run_case

DEFAULT_MODEL = "bytedance-seed/seedream-4.5"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one garment-consistency experiment case")
    parser.add_argument("case_id")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--cases", type=Path, default=Path("cases.json"))
    parser.add_argument("--prompt", type=Path, default=Path("prompts/baseline.txt"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs"))
    parser.add_argument("--allow-holdout", action="store_true")
    return parser


def main() -> int:
    """Run the CLI and return a process exit code."""

    args = _parser().parse_args()

    try:
        cases = load_cases(args.cases)
        case = cases[args.case_id]
        if case.split == "holdout" and not args.allow_holdout:
            print(f"holdout case {case.id} requires --allow-holdout")
            return 2

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("OPENROUTER_API_KEY is not set")
            return 2

        prompt = render_prompt(case, args.prompt)
        result_dir = run_case(
            case=case,
            prompt=prompt,
            model=args.model,
            strategy="baseline",
            api_key=api_key,
            output_root=args.output_root,
        )
    except KeyError:
        print(f"unknown case: {args.case_id}")
        return 2
    except (CaseError, GenerationError, FileExistsError, OSError, ValueError) as exc:
        print(str(exc))
        return 1

    print(result_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
