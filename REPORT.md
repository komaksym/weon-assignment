# Improving garment consistency in black-box AI photoshoots

## Executive summary

The task is to compose a person, an environment, and a garment packshot while preserving product identity. I tested two practical improvement directions around a closed-source image model:

1. **Structured garment prompting:** a VLM extracts visible garment attributes and injects them as hard constraints.
2. **Best-of-two selection:** generate two structured candidates and use a VLM to select the stronger one.

The direct baseline was ultimately the best operational choice. On three development cases, a blinded VLM comparison tied all strategies at `0.8889`; manual means were baseline `0.6833`, structured `0.6500`, and best-of-two `0.6500`. Best-of-two cost roughly twice as much and was about ten times slower than baseline. The frozen baseline was therefore applied once to two holdouts without tuning or resampling.

The holdout automatic evaluator scored both outputs `1.0`, but manual scores were `0.5833` and `0.7500`. This gap is itself an important result: broad color, garment presence, and coarse silhouette are preserved reasonably well, while logos, exact construction, and material details remain unreliable and are often overestimated by a VLM judge.

![Development comparison](submission/figures/development-comparison.jpg)

## Failure-mode analysis

The observed failures form a compact taxonomy:

- **Branding loss or hallucination:** logos and text disappear, become unreadable, or turn into approximate marks.
- **Construction drift:** buttons, zippers, pockets, seams, panels, collars, soles, and closures move or simplify.
- **Texture simplification:** suede/leather boundaries, technical fabric, waxed coating, corduroy, and stitching lose specificity.
- **Color drift:** lighting can shift dark green toward brown/olive even when color is explicitly constrained.
- **Evaluator overconfidence:** the VLM often rewards coarse visual similarity while missing absent branding and incorrect geometry.
- **Selection unreliability:** best-of-two tied frequently and selected candidate A deterministically; on D03, the human reviewer preferred B.

These failures matter because garment identity is not just category recognition. A plausible pair of brown shoes is not necessarily the referenced product.

## Experiment design

Five cases were used: D01-D03 for development and H01-H02 as frozen holdouts. All images came from the assignment-provided set. The generator was `google/gemini-3.1-flash-lite-image` through OpenRouter, requesting one `1K`, `3:4` output. References were EXIF-oriented, resized to at most 1024 pixels, composited onto white when transparent, and encoded as JPEG quality 85.

Each candidate was scored on six dimensions using `1 / 0.5 / 0 / -1`:

- color;
- print/logo;
- silhouette/length;
- construction details;
- texture/material;
- garment presence.

`-1` means genuinely not applicable and is excluded from the mean. Comparative evaluation uses opaque candidate IDs with a deterministic case-specific permutation, so the judge cannot infer which output is baseline or an attempted improvement. A manual sanity check uses the same rubric.

## Development results

| Strategy | Blinded automatic mean | Manual mean | Average method cost | Average method latency |
| --- | ---: | ---: | ---: | ---: |
| Baseline | **0.8889** | **0.6833** | **$0.034466** | **5.48 s** |
| Structured | **0.8889** | 0.6500 | $0.035331 | 8.16 s |
| Best of two | **0.8889** | 0.6500 | $0.072624 | 54.89 s |

Structured prompting did not produce a consistent fidelity gain. Best-of-two added a second generation and a comparison call but did not improve the manual aggregate. The baseline was frozen because it was simplest, cheapest, fastest, and manually strongest.

## Frozen holdout results

![H01 footwear holdout](submission/figures/H01-contact-sheet.jpg)

![H02 shorts holdout](submission/figures/H02-contact-sheet.jpg)

| Case | Automatic | Manual | Generation cost | Total experiment latency |
| --- | ---: | ---: | ---: | ---: |
| H01 sneakers | 1.0000 | 0.5833 | $0.034466 | 8.43 s |
| H02 shorts | 1.0000 | 0.7500 | $0.034934 | 10.25 s |
| Mean | **1.0000** | **0.6667** | $0.034700 | 9.34 s |

H01 preserved the brown/orange palette and low-top sneaker identity, but branding was not legible and the toe, sole, panel, and material details drifted. The automatic evaluator also marked shoe silhouette as not applicable, which the human review rejected.

H02 preserved olive color, shorts length, the double-button waist, belt loops, and the broad cargo layout. Branding, zipper placement, panel geometry, stitching, and technical-fabric texture were only approximate.

The frozen run used exactly two image requests and two evaluator requests, with no retries or resampling. Generation cost was `$0.06940025`; rough evaluation added `$0.0026784`. Results were frozen as observed.

## Practical conclusions

The baseline is a useful low-cost first pass when coarse garment identity is sufficient. It is not reliable enough for brand-critical catalog production where exact logos, seams, closures, or materials must match.

With more time, I would prioritize:

1. garment-region crops for both automatic and human evaluation;
2. explicit OCR/logo checks instead of relying on a general VLM score;
3. deterministic image metrics for color and local structure alongside VLM judgment;
4. targeted inpainting only on failed garment regions rather than full-image regeneration;
5. a larger, stratified set covering text-heavy products, patterned garments, layered outfits, and small accessories.

The main methodological lesson is that automatic evaluation must be blinded and audited against human judgment. In this experiment, the VLM was useful for orchestration and rough diagnostics, but not trustworthy as the sole measure of product fidelity.
