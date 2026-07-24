# Slice 3 — consolidated development experiments

## Goal

Compare a direct baseline with two practical garment-consistency improvements on D01-D03, then freeze one strategy for holdout evaluation.

## Fixed experiment

- Generator: `google/gemini-3.1-flash-lite-image`.
- Evaluator: `openai/gpt-4.1-mini`.
- Output: one `1K`, `3:4` image per generation request.
- Reference order: person/model, environment, garment packshot(s).
- Preprocessing: EXIF orientation, maximum 1024 pixels, white transparency composition, JPEG quality 85.
- Holdout cases: inaccessible in this workflow.
- Retries: none.

The initially selected Gemini Flash Lite evaluator extracted packshot attributes but repeatedly returned a provider error when generated human images were included. GPT-4.1 Mini completed the comparison and was frozen as evaluator before the successful matrix.

## Strategy matrix

For each of D01, D02, and D03:

1. Extract visible garment facts from the packshot using the fixed six-dimension schema.
2. Generate one `baseline` candidate with the existing baseline prompt.
3. Generate `structured_a` using the extracted attributes as hard constraints.
4. Generate `structured_b` with the identical structured prompt.
5. Map baseline, A, and B to opaque `candidate_1..3` IDs using a deterministic case-specific SHA-256 permutation.
6. Record that mapping, show only opaque IDs to the evaluator, and score all three against the packshot.
7. Treat A as the standalone `structured` result.
8. Map the scores back to their strategies and select A or B for `best_of_two`; ties select A.

This produces nine image calls and six VLM calls in a fresh matrix. Candidate A is reused rather than regenerated for the standalone structured comparison. Existing image artifacts may be rescored with three comparison-only VLM calls and zero image calls.

## Rubric

Each generated result receives one score for:

- color;
- print/logo;
- silhouette/length;
- construction details;
- texture/material;
- garment presence.

Allowed values:

- `1` — preserved;
- `0.5` — partially preserved;
- `0` — drifted or missing;
- `-1` — genuinely not applicable in the source packshot.

Applicability is source-level. Baseline, A, and B must have an identical `-1` mask; mismatched masks are rejected before means or selection are calculated. The mean excludes the shared `-1` dimensions.

## Evidence

The workflow must produce:

- original generation image and metadata for all nine requests;
- `attributes.json` and `evaluation.json` for each case;
- the recorded opaque candidate mapping for every comparison;
- `selection.json` and the selected best-of-two image for each case;
- one contact sheet per case;
- `results.csv` with automatic scores, generation/setup/selection costs, and latency;
- `manual_scores.csv` with the same rubric and selector-agreement field;
- `development_summary.json` with request counts, aggregate costs/latencies, automatic strategy means, and pending winner status.

Generated images remain in the workflow artifact and are not committed.

## Manual sanity check

After the single paid workflow completes:

- open every contact sheet;
- score all nine strategy rows manually;
- verify whether each VLM best-of-two choice is reasonable;
- record disagreements rather than rerunning candidates;
- compare blinded automatic and manual strategy means;
- consider complete end-to-end cost and latency before selecting the winner.

## Decision gate

Record one frozen winner: `baseline`, `structured`, or `best_of_two`.

Do not run or inspect H01/H02 until that decision, generator, prompt behavior, preprocessing, selector, and rubric are committed. No development resampling is allowed merely because a result is visually weak; weak outputs are part of the evidence.
