# Slice 3 development experiment

## Status

`complete — freeze baseline for slice 4`

The consolidated D01-D03 matrix completed successfully and compared the direct baseline, structured garment prompting, and VLM-selected best-of-two. The automatic metric gave a small advantage to the two structured methods, but manual review found no consistent fidelity improvement and selected the baseline after considering cost, latency, and robustness.

## Execution

- Workflow run: `30102014361`
- Artifact: `development-matrix-30102014361`
- Generator: `google/gemini-3.1-flash-lite-image`
- Evaluator: `openai/gpt-4.1-mini`
- Development cases: D01, D02, D03
- Image requests: `9`
- VLM requests: `6`
- Holdout requests: `0`
- Automatic retries: `0`
- Final-matrix API-reported cost: `$0.3213208`
- Final-matrix generation latency: `152.0235 s`
- Final-matrix VLM latency: `26.9808 s` including attribute extraction and comparison

The first isolated execution used `google/gemini-2.5-flash-lite` as evaluator. It successfully extracted D01 garment attributes and generated all three D01 images, then returned a provider error whenever a generated human image was included for scoring. An exact four-image comparison with GPT-4.1 Mini succeeded in `6.7286 s` for `$0.0027668`, so the evaluator was replaced before the final matrix. Known slice-3 exploration and final-matrix spend totals `$0.42923385`; billing for the failed evaluator responses is unknown.

## Aggregate comparison

| Strategy | Automatic mean | Manual mean | Average method cost | Average method latency |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 0.7222 | **0.6833** | **$0.034466** | **5.48 s** |
| Structured | **0.7500** | 0.6500 | $0.034613 | 5.38 s |
| Best of two | **0.7500** | 0.6500 | $0.071923 | 51.41 s |

Method cost for best-of-two includes both structured image candidates and the comparison VLM request. Attribute extraction is reported separately because it is shared setup for the two structured directions.

## Manual sanity check

| Case | Automatic selector | Human selector assessment | Main observation |
| --- | --- | --- | --- |
| D01 shorts | Structured A | Tie; A acceptable | Both structured candidates and baseline lose the logo and exact pocket/panel geometry. |
| D02 sneakers | Structured A | Tie; A acceptable | Brown/tan shape is preserved, but ARIGATO branding is absent; automatic `1.0` scores are overconfident. |
| D03 jacket | Structured A | **Disagree; B looked closer** | A shifts toward brown/olive in sunlight; B better preserves dark-green color and collar contrast. |

The selector chose A for all three cases because automatic scores tied. The deterministic A tie-break is reproducible, but D03 shows that it is not reliably aligned with human preference.

## Failure taxonomy

- **Branding loss:** The shorts and sneaker logos disappear under every strategy.
- **Construction drift:** Pockets, zippers, panel boundaries, closures, and outsole geometry become approximations.
- **Texture simplification:** Technical fabric, suede/leather separation, waxed coating, and corduroy are only partially retained.
- **Lighting-driven color drift:** Structured D03 is pushed toward brown/olive despite explicit dark-green constraints.
- **Evaluator overconfidence:** Small footwear details received perfect automatic scores even when branding and exact construction were visibly absent.
- **Selection overhead without benefit:** Best-of-two doubled method cost and substantially increased latency while selecting no manual winner that improved the aggregate score.

## Decision

`baseline`

Freeze the following for slice 4:

- strategy: direct baseline, one candidate;
- generator: `google/gemini-3.1-flash-lite-image`;
- prompt: `prompts/baseline.txt`;
- output: `1K`, `3:4`;
- reference order: person, environment, garment packshot(s);
- preprocessing: EXIF orientation, maximum 1024 pixels, white transparency composition, JPEG quality 85;
- evaluator for rough scoring: `openai/gpt-4.1-mini`;
- manual rubric: color, print/logo, silhouette/length, construction details, texture/material, presence;
- retries and resampling: none.

The automatic structured advantage is only `0.0278`, reverses under manual review, and does not justify extra prompt/evaluator complexity. Baseline is the simplest, cheapest, and most robust method supported by this development set.

H01 and H02 remain ungenerated and uninspected. They may now be evaluated once in slice 4 using the frozen configuration.
