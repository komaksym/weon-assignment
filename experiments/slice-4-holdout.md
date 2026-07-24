# Slice 4 frozen holdout evaluation

## Status

`complete - results frozen without retuning`

## Execution

- Workflow run: `30113526488`
- Artifact: `frozen-holdouts-30113526488`
- Cases: H01, H02 only
- Strategy: direct baseline, one candidate
- Generator: `google/gemini-3.1-flash-lite-image`
- Evaluator: `openai/gpt-4.1-mini`
- Image requests: `2`
- Evaluator requests: `2`
- Development requests: `0`
- Automatic retries/resampling: `0`
- Generation cost: `$0.06940025`
- Evaluation cost: `$0.0026784`
- Total experiment cost: `$0.07207865`
- Generation latency: `13.1647 s`
- Evaluation latency: `5.5149 s`

The first execution stopped during input preparation because the existing safety guard requires `--allow-holdout`. It made zero API requests. The final workflow passed the flag explicitly and completed once.

## Results

| Case | Automatic | Manual | Generation cost | End-to-end experiment latency |
| --- | ---: | ---: | ---: | ---: |
| H01 sneakers | **invalid — source N/A violation** | 0.5833 | $0.034466 | 8.43 s |
| H02 shorts | 1.0000 | 0.7500 | $0.034934 | 10.25 s |
| Manual mean | — | **0.6667** | $0.034700 | 9.34 s |

No two-case automatic mean is reported. H01's raw evaluator response used `silhouette_length = -1`, but the frozen source-level applicability mask requires all six dimensions for both footwear and shorts. The raw response is preserved in the workflow artifact and the committed CSV, while its mean is marked invalid rather than recomputed or silently denominator-shifted.

- **H01:** brown/orange color and low-top sneaker identity survive, but ARIGATO branding is not legible and toe, sole, panel, and material details are approximate.
- **H02:** olive color, length, double-button waist, belt loops, and cargo layout survive. The logo becomes an approximate dark mark, while zipper placement, panel geometry, stitching, and technical-fabric texture drift.

## Durable visual evidence

Each committed holdout figure contains the packshot, full generated result, and a deterministic garment-region detail crop. The crops affect presentation only, not generation or scoring.

- H01 normalized crop: `[0.23, 0.77, 0.78, 0.99]`; pixel box on the `896×1200` result: `[206, 924, 699, 1188]`.
- H02 normalized crop: `[0.29, 0.39, 0.71, 0.69]`; pixel box: `[260, 468, 636, 828]`.

The same data is stored in `submission/figures/crop-metadata.json`.

## Robustness and failure modes

The frozen baseline generalizes mechanically across footwear and technical shorts, two different people, and two environments. Garment presence, broad color, and coarse silhouette are robust. Fine identity is not:

- logos and exact text are dropped or hallucinated;
- construction geometry becomes approximate;
- material boundaries and texture simplify;
- small details receive overconfident VLM scores;
- evaluator applicability errors can invalidate aggregate metrics;
- full-body framing requires a durable detail crop for independent review.

## Decision

No holdout-driven model, prompt, preprocessing, candidate, rubric, or manual-score change was made. The baseline remains the final method because development comparisons showed no blinded automatic advantage for structured prompting or best-of-two, while baseline was cheaper, faster, and manually strongest. The holdouts confirm that this is a practical but incomplete solution: coarse garment identity is preserved more reliably than brand-level or construction-level fidelity.
