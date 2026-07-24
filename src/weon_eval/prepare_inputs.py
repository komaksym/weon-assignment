"""Command-line entry point for preparing one case's local references."""

from __future__ import annotations

import argparse
from pathlib import Path

from weon_eval.assets import AssetError, prepare_case_inputs
from weon_eval.cases import CaseError, load_cases


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare one experiment case's input images")
    parser.add_argument("case_id")
    parser.add_argument("--cases", type=Path, default=Path("cases.json"))
    parser.add_argument("--sources", type=Path, default=Path("asset_sources.json"))
    parser.add_argument("--allow-holdout", action="store_true")
    return parser


def main() -> int:
    """Prepare one case and return a process exit code."""

    args = _parser().parse_args()
    try:
        cases = load_cases(args.cases)
        case = cases[args.case_id]
        if case.split == "holdout" and not args.allow_holdout:
            print(f"holdout case {case.id} requires --allow-holdout")
            return 2
        prepared = prepare_case_inputs(case, args.sources)
    except KeyError:
        print(f"unknown case: {args.case_id}")
        return 2
    except (AssetError, CaseError, OSError, ValueError) as exc:
        print(str(exc))
        return 1

    for path in prepared:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
