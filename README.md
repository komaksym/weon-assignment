# WEON Garment Consistency Experiment

A black-box image-generation study of one practical question:

> Can prompt, reference-conditioning, model, or multi-step pipeline changes preserve exact garment identity better than a direct generation baseline?

## Final verdict

**No tested method demonstrated a reliable improvement over the direct baseline.**

The strongest promoted pipeline scored essentially the same as direct generation while costing about twice as much. Several methods received perfect or near-perfect automatic scores despite visibly incorrect logos, closures, panels, and materials. The operational recommendation is therefore:

- use `lite_direct` for a low-cost first pass when coarse garment identity is sufficient;
- do not treat the current output as reliable for brand-critical catalog work;
- gate production output with garment-region checks, especially OCR/logo and construction-detail checks;
- repair or resample only candidates that fail those checks.

| Method | Automatic mean | Average cost | Average latency | Decision |
| --- | ---: | ---: | ---: | --- |
| `lite_direct` | **0.9762** | **$0.0360** | **8.53 s** | Keep as baseline |
| `lite_duplicate_garment` | 0.9940 | $0.0365 | 9.00 s | Nominal unpaired lead; not visually reliable |
| `lite_identity_tight_crop` | 0.9936 | $0.0360 | 8.76 s | Lost in the later paired check |
| `identity_tight_crop_best_of_two` | 0.9750 | $0.0727 | 15.01 s | No gain at roughly 2x cost |

A same-run D01-D03 control gave `lite_direct = 1.0000`, identity plus negative constraints `= 1.0000`, and identity plus tight crop `= 0.9667`. The perfect scores were not trustworthy: visual review still found product-identity errors.

The completed attributed author review likewise found substantial drift. On the initial D01-D03 matrix, baseline scored `0.500` and structured/best-of-two scored `0.667`; both frozen baseline holdouts scored `0.500`. Best-of-two selected the structured image in every development case, so those equal human means are duplicate evidence rather than independent confirmation.

**Start with [REPORT.md](REPORT.md).** It is the short submission report and includes the failure taxonomy, methods, frozen evaluation, visual evidence, results, limitations, and production recommendation.

![Development comparison](submission/figures/development-comparison.jpg)

The compact image above is report-only. The completed [author human-review results](submission/HUMAN_REVIEW_RESULTS.md) use the dedicated [protocol](submission/HUMAN_REVIEW.md) and high-resolution sheets. All 11 overall decisions are stored as [JSON](submission/human-review-ratings.json) and [CSV](submission/human-review-ratings.csv).

## What was tested

The search covered four distinct levers around closed-source models:

1. **Prompt engineering** - structured garment descriptions, identity-priority instructions, and explicit negative constraints.
2. **Input conditioning** - tight crops, background removal, detail boards, reference ordering, and duplicated garment references.
3. **Pipeline design** - best-of-two selection and a garment-focused repair pass.
4. **Model comparison** - multiple image models under the same frozen evaluation contract.

Five distinct assignment cases were used: D01-D03 for development and H01-H02 as frozen holdouts. Development cases were sampled repeatedly to estimate stochastic behavior.

## Evaluation contract

The final evaluator was frozen before paid execution:

- evaluator: `openai/gpt-4.1-mini`;
- dimensions: color, print/logo, silhouette/length, construction details, texture/material, and presence;
- scores: `1`, `0.5`, `0`, or `-1` only when genuinely not applicable;
- source-level applicability masks;
- opaque candidate IDs where comparison or selection was used;
- unchanged aggregation;
- raw evaluator JSON persisted before validation;
- no holdout access during method selection;
- no retries or score-driven prompt changes.

A separate ChatGPT visual assessment was used as a sanity check. It was **not** independent human evaluation. The human sanity-check path uses one overall visible garment-fidelity score per output and full-resolution evidence; its ratings will be attributed to the assignment author rather than presented as independent review.

## Repository map

- [`REPORT.md`](REPORT.md) - final 10-minute report.
- [`submission/HUMAN_REVIEW.md`](submission/HUMAN_REVIEW.md) - app workflow, rubric, attribution, and recording contract.
- [`submission/HUMAN_REVIEW_RESULTS.md`](submission/HUMAN_REVIEW_RESULTS.md) - completed attributed human-review summary.
- [`submission/human-review-ratings.csv`](submission/human-review-ratings.csv) - portable per-output author ratings.
- [`submission/review/`](submission/review/) - high-resolution D01-D03 and H01-H02 review sheets.
- [`submission/figures/`](submission/figures/) - compact report figures and UI evidence.
- [`experiments/`](experiments/) - detailed execution records, metrics, costs, and evaluator caveats.
- [`src/weon_eval/`](src/weon_eval/) - generation, evaluation, search, reporting, and local human-review code.
- [`tests/`](tests/) - deterministic tests; no test performs a paid API call.
- [`specs/`](specs/) - precommitted experiment contracts.

## Run locally

Requirements: Python 3.12+ and `uv`.

```bash
uv sync --dev
cp .env.example .env
export OPENROUTER_API_KEY="..."
```

### Inspect or reproduce the author human review

No API key or paid request is needed:

```bash
uv run weon-human-review
```

The command opens a five-case desktop evaluator with large source/candidate panes. It loads the completed 11-output author review, auto-saves edits, and exports JSON, CSV, and submission-ready Markdown.

### Prepare and run one direct baseline case

```bash
uv run weon-prepare-inputs D01
uv run weon-eval D01
```

### Reproduce the fixed development comparison

```bash
for case_id in D01 D02 D03; do
  uv run weon-prepare-inputs "$case_id"
done

uv run weon-development
```

The holdout command is intentionally separate and explicit:

```bash
uv run weon-prepare-inputs H01 --allow-holdout
uv run weon-prepare-inputs H02 --allow-holdout
uv run weon-holdout
```

Raw assignment inputs and standalone generated outputs are not committed. Compact report figures and high-resolution composite review sheets preserve the durable visual evidence.

## Validation

```bash
uv run ruff check .
uv run mypy src
uv run pytest
uv build
```

Normal CI never performs a paid model request. Paid workflows first run dependency sync, linting, strict type checking, tests, and package build.

## Limitations and disclosure

- The study has five distinct cases, with repeated development samples rather than a large benchmark.
- The automatic judge saturated and overestimated exact product fidelity.
- One attributed author review was completed; no independent or multi-rater human evaluation was performed.
- Image generation, automatic scoring, and analysis used AI systems; their roles are documented in the report and experiment records.
- The last observed vendor-key allowance was about `$0.03`; no further meaningful paid run is justified.
