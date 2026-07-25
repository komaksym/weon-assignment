"""CLI for the frozen H01-H02 evaluation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from weon_eval.holdout import (
    DEFAULT_EVALUATOR_MODEL,
    DEFAULT_GENERATOR_MODEL,
    run_holdouts,
)
from weon_eval.openrouter import GenerationError, generate_image
from weon_eval.vlm import VlmError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the frozen baseline on H01-H02")
    parser.add_argument("--cases", type=Path, default=Path("cases.json"))
    parser.add_argument("--prompt", type=Path, default=Path("prompts/baseline.txt"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs/holdout"))
    parser.add_argument("--generator-model", default=DEFAULT_GENERATOR_MODEL)
    parser.add_argument("--evaluator-model", default=DEFAULT_EVALUATOR_MODEL)
    return parser


def main() -> int:
    """Run the holdout evaluation and return a process exit code."""

    args = _parser().parse_args()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY is not set")
        return 2
    try:
        result = run_holdouts(
            cases_path=args.cases,
            prompt_path=args.prompt,
            api_key=api_key,
            output_root=args.output_root,
            generator_model=args.generator_model,
            evaluator_model=args.evaluator_model,
            generator=generate_image,
        )
    except (FileExistsError, GenerationError, KeyError, OSError, ValueError, VlmError) as exc:
        print(str(exc))
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
