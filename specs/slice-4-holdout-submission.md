# Slice 4 - frozen holdouts and submission

## Goal

Apply the slice-3 winner exactly once to H01 and H02, freeze the observed results without tuning, and package the repository for a ten-minute review.

## Frozen configuration

- Strategy: direct `baseline`, one candidate.
- Generator: `google/gemini-3.1-flash-lite-image`.
- Prompt: `prompts/baseline.txt`.
- Output: `1K`, `3:4`.
- Reference order: person, environment, garment packshot(s).
- Preprocessing: EXIF orientation, maximum 1024 pixels, white transparency composition, JPEG quality 85.
- Evaluator: `openai/gpt-4.1-mini`.
- Rubric: color, print/logo, silhouette/length, construction details, texture/material, presence.
- Retries and resampling: none.

## Execution

1. Prepare only H01 and H02 from the assignment source manifest.
2. Generate one baseline image for each holdout.
3. Score each result against its garment packshot using opaque `candidate_1` identity.
4. Persist image metadata, evaluator output, automatic scores, cost, latency, and a reviewer-attributed score template.
5. Create one compact garment-reference/result contact sheet per holdout.
6. Visually assess both holdouts and record reviewer identity and method and freeze the results without changing the model, prompt, preprocessing, or rubric.

The paid workflow must make exactly two image-generation requests and two evaluator requests. It must never access D01-D03 and must have no automatic retry.

## Submission package

- `REPORT.md`: 1-4 page-equivalent report covering failure modes, strategies, evaluation, results, costs, robustness, limitations, and next steps.
- `experiments/slice-4-holdout-results.csv`: compact automatic evidence.
- `experiments/slice-4-holdout-chatgpt-visual-scores.csv`: completed ChatGPT visual assessment; no independent human reviewer participated.
- `submission/figures/`: compressed before/after contact sheets needed for the assignment deliverable.
- README reproduction instructions for development and frozen holdout runs.

Only final compressed contact sheets are committed as an explicit submission exception. Raw input images, standalone generated images, API keys, and transient workflow artifacts remain uncommitted.

## Decision gate

The holdout outputs are reported exactly as observed. No holdout-driven prompt change, regeneration, candidate selection, or score editing is permitted. The final repository must be runnable and understandable in roughly ten minutes.