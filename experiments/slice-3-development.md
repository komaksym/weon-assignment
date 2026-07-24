# Slice 3 development experiment

## Status

`complete — freeze baseline for slice 4`

The consolidated D01-D03 matrix compared the direct baseline, structured garment prompting, and VLM-selected best-of-two. A follow-up blinded rescore reused the existing nine images with opaque candidate IDs and a recorded deterministic permutation. The blinded evaluator tied all three strategies, while the ChatGPT visual assessment favored the baseline after cost, latency, selector reliability, and complexity were considered.

## Execution

- Original generation workflow: `30102014361`
- Original artifact: `development-matrix-30102014361`
- Blinded rescore workflow: `30111314191`
- Blinded artifact: `blinded-rescore-30111314191`
- Generator: `google/gemini-3.1-flash-lite-image`
- Evaluator: `openai/gpt-4.1-mini`
- Development cases: D01, D02, D03
- Image requests: `9`
- Attribute-extraction requests: `3`
- Original treatment-labelled comparison requests: `3`
- Blinded comparison requests: `3`
- Holdout requests: `0`
- Automatic retries: `0`
- Original final-matrix API-reported cost: `$0.3213208`
- Blinded rescore cost: `$0.0079808`
- Blinded rescore latency: `20.7184 s`
- Known slice-3 exploration and experiment spend: `$0.43721465`; billing for failed evaluator responses remains unknown.

The first isolated execution used `google/gemini-2.5-flash-lite` as evaluator. It extracted D01 garment attributes and generated all three D01 images, then returned a provider error whenever a generated human image was included for scoring. GPT-4.1 Mini completed the exact comparison and was frozen as evaluator before the successful matrix.

## Aggregate comparison

| Strategy | Blinded automatic mean | ChatGPT visual-assessment mean | Average method cost | Average method latency |
| --- | ---: | ---: | ---: | ---: |
| Baseline | **0.8889** | **0.6833** | **$0.034466** | **5.48 s** |
| Structured | **0.8889** | 0.6500 | $0.035331 | 8.16 s |
| Best of two | **0.8889** | 0.6500 | $0.072624 | 54.89 s |

Structured and best-of-two totals each include the garment-attribute extraction required to construct their prompts. Best-of-two additionally includes both structured generations and the blinded comparison request. Shared extraction remains counted once per case in the whole-matrix total.

The earlier treatment-labelled automatic means—baseline `0.7222`, structured `0.7500`, and best-of-two `0.7500`—are superseded as comparative evidence. Once the same images were rescored behind opaque case-specific IDs, every strategy tied at `0.8889`. This removes the apparent automatic advantage for structured prompting.

## ChatGPT visual assessment

ChatGPT assigned these scores from the contact sheets. They are a separate AI judgment path, not independent human evaluation.

| Case | Blinded selector | ChatGPT selector assessment | Main observation |
| --- | --- | --- | --- |
| D01 shorts | Structured A | Tie; A acceptable | All variants lose exact logo and pocket/panel geometry. |
| D02 sneakers | Structured A | Tie; A acceptable | Shape and color are preserved, but ARIGATO branding is absent and exact material/panel fidelity is weaker than the automatic perfect score suggests. |
| D03 jacket | Structured A | **Disagree; B looked closer** | A shifts toward brown/olive in sunlight; B better preserves dark-green color and collar contrast. |

The selector still chose A for all three cases. D01 and D02 are reasonable ties, while D03 remains a ChatGPT-assessment disagreement. The source-level N/A mask matched across all three candidates in every blinded comparison; the evaluator boundary now rejects future mismatches before scoring or selection.

## Failure taxonomy

- **Branding loss:** The shorts and sneaker logos disappear under every strategy.
- **Construction drift:** Pockets, zippers, panel boundaries, closures, and outsole geometry become approximations.
- **Texture simplification:** Technical fabric, suede/leather separation, waxed coating, and corduroy are only partially retained.
- **Lighting-driven color drift:** Structured D03 is pushed toward brown/olive despite explicit dark-green constraints.
- **Evaluator overconfidence:** The blinded evaluator assigned high or perfect scores despite visible missing branding and construction differences.
- **Selection overhead without benefit:** Best-of-two more than doubled method cost and substantially increased latency without improving the ChatGPT visual-assessment aggregate.

## Decision

`baseline`

Freeze the following for slice 4:

- strategy: direct baseline, one candidate;
- generator: `google/gemini-3.1-flash-lite-image`;
- prompt: `prompts/baseline.txt`;
- output: `1K`, `3:4`;
- reference order: person, environment, garment packshot(s);
- preprocessing: EXIF orientation, maximum 1024 pixels, white transparency composition, JPEG quality 85;
- evaluator for rough scoring: `openai/gpt-4.1-mini` with opaque candidate identity where comparisons are made;
- visual-assessment rubric: color, print/logo, silhouette/length, construction details, texture/material, presence;
- retries and resampling: none.

The blinded automatic comparison provides no strategy advantage. Baseline selection is operationally justified by lower cost, latency, and complexity; the ChatGPT visual-assessment lead is supplemental rather than human-grounded evidence. Baseline remains the ChatGPT visual-assessment leader, is the cheapest and fastest method, avoids attribute-extraction and selection dependencies, and is therefore the strongest frozen choice for the two holdouts.

H01 and H02 remain ungenerated and uninspected. They may now be evaluated once in slice 4 using the frozen configuration.
