# Slice 3 development experiment

## Status

`complete — freeze baseline for slice 4`

The consolidated D01-D03 matrix completed successfully and compared the direct baseline, structured garment prompting, and VLM-selected best-of-two. The automatic evaluator slightly favored the structured methods, but it was shown treatment labels and is therefore retained only as non-blinded exploratory evidence. Manual review found no consistent fidelity improvement and selected the baseline after considering cost, latency, and robustness.

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
| Structured | 0.7500 | 0.6500 | $0.035331 | 8.16 s |
| Best of two | 0.7500 | 0.6500 | $0.072641 | 54.19 s |

Structured and best-of-two totals each include the garment-attribute extraction request required to construct their prompts. Best-of-two additionally includes both structured generations and the comparison VLM request. The global final-matrix total remains unchanged because shared extraction is counted once per case at the matrix level.

The automatic means are not treated as independent strategy evidence because the evaluator prompt and schema exposed the identities `baseline`, `structured_a`, and `structured_b`. They remain useful as rough diagnostics only; no additional calls were made to rescore the existing images.

## Manual sanity check

| Case | Automatic selector | Human selector assessment | Main observation |
| --- | --- | --- | --- |
| D01 shorts | Structured A | Tie; A acceptable | Both structured candidates and baseline lose the logo and exact pocket/panel geometry. |
| D02 sneakers | Structured A | Tie; A acceptable | Brown/tan shape is preserved, but ARIGATO branding is absent; automatic `1.0` scores are overconfident. |
| D03 jacket | Structured A | **Disagree; B looked closer** | A shifts toward brown/olive in sunlight; B better preserves dark-green color and collar contrast. |

The selector chose A for all three cases because automatic scores tied. The deterministic A tie-break is reproducible, but D03 shows that it is not reliably aligned with human preference. The current artifact used the same N/A mask across candidates; the evaluator boundary now rejects future comparisons whose candidate-specific `-1` masks differ.

## Failure taxonomy

- **Branding loss:** The shorts and sneaker logos disappear under every strategy.
- **Construction drift:** Pockets, zippers, panel boundaries, closures, and outsole geometry become approximations.
- **Texture simplification:** Technical fabric, suede/leather separation, waxed coating, and corduroy are only partially retained.
- **Lighting-driven color drift:** Structured D03 is pushed toward brown/olive despite explicit dark-green constraints.
- **Evaluator overconfidence:** Small footwear details received perfect automatic scores even when branding and exact construction were visibly absent.
- **Non-blinded evaluator:** Treatment labels were visible, so small automatic differences cannot be interpreted as clean causal evidence.
- **Selection overhead without benefit:** Best-of-two more than doubled method cost and substantially increased latency while selecting no manual winner that improved the aggregate score.

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

The automatic `0.0278` structured difference is not used to support the decision because the comparison was non-blinded. Baseline is selected from the manual results, corrected end-to-end method costs and latencies, selector disagreement, and lower operational complexity.

H01 and H02 remain ungenerated and uninspected. They may now be evaluated once in slice 4 using the frozen configuration.
