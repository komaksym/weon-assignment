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
| H01 sneakers | 1.0000 | 0.5833 | $0.034466 | 8.43 s |
| H02 shorts | 1.0000 | 0.7500 | $0.034934 | 10.25 s |
| Mean | **1.0000** | **0.6667** | $0.034700 | 9.34 s |

The automatic evaluator is materially overconfident on both holdouts.

- **H01:** brown/orange color and low-top sneaker identity survive, but ARIGATO branding is not legible and toe, sole, panel, and material details are approximate. The evaluator incorrectly marked silhouette as not applicable even though shoe shape is directly comparable.
- **H02:** olive color, length, double-button waist, belt loops, and cargo layout survive. The logo becomes an approximate dark mark, while zipper placement, panel geometry, stitching, and technical-fabric texture drift.

## Robustness and failure modes

The frozen baseline generalizes mechanically across footwear and technical shorts, two different people, and two environments. Garment presence, broad color, and coarse silhouette are robust. Fine identity is not:

- logos and exact text are dropped or hallucinated;
- construction geometry becomes approximate;
- material boundaries and texture simplify;
- small details receive overconfident VLM scores;
- full-body framing makes footwear details especially hard to inspect.

## Decision

No holdout-driven change was made. The baseline remains the final method because development comparisons showed no blinded automatic advantage for structured prompting or best-of-two, while baseline was cheaper, faster, and manually strongest. The holdouts confirm that this is a practical but incomplete solution: coarse garment identity is preserved more reliably than brand-level or construction-level fidelity.
