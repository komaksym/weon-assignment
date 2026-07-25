# Budgeted Garment-Consistency Method Search

## Goal

Use the remaining OpenRouter key allowance down to a hard floor of `$10.00` while testing materially different garment-preservation methods. Preserve evaluation integrity: no method-specific rubric, judge prompt, applicability rule, score transformation, or post-hoc candidate exclusion.

## Evaluation protocol — frozen before paid execution

- Evaluator: `openai/gpt-4.1-mini`.
- Rubric: color, print/logo, silhouette/length, construction details, texture/material, garment presence.
- Scores: `1`, `0.5`, `0`, and `-1` only where the source attribute is genuinely not applicable.
- Candidate identity: opaque single-candidate ID (`candidate_1`).
- Evaluator input: source garment packshot(s), then the final candidate image.
- Evaluator prompt and JSON schema: one fixed implementation shared by every method.
- Applicability masks are source-level and declared before execution: D01 and D02 use all six dimensions; D03 excludes only `print_logo`.
- Raw evaluator JSON is persisted before validation. Invalid applicability responses remain auditable and are excluded from aggregation; they are never repaired or rescored automatically.
- No ChatGPT or human score influences automated method selection. Reviewer-neutral score templates are produced for later review.

## Methods

The search uses a predeclared round-robin queue. Every method runs on D01, D02, and D03 before the next replicate begins.

1. `lite_direct` — existing Nano Banana 2 Lite baseline.
2. `lite_identity_prompt` — same model with a fixed identity-priority prompt emphasizing exact product details over styling.
3. `lite_detail_board` — same prompt/model, but the garment reference is replaced by a deterministic board containing the full packshot plus fixed detail crops.
4. `lite_two_pass_repair` — direct candidate followed by one fixed garment-only repair edit using the original packshot; the evaluator sees only the repaired image.
5. `nano25_direct` — direct generation with `google/gemini-2.5-flash-image`.
6. `nano31_direct` — direct generation with `google/gemini-3.1-flash-image`.
7. `nano31_detail_board` — full Nano Banana 2 with the deterministic garment detail board.
8. `seedream_direct` — direct generation with `bytedance-seed/seedream-4.5`.
9. `seedream_detail_board` — Seedream with the deterministic garment detail board.
10. `gpt_image_1_mini_direct` — direct generation with `openai/gpt-image-1-mini`.
11. `gpt_image_1_mini_detail_board` — GPT Image 1 Mini with the deterministic garment detail board.
12. `gpt_image_2_direct` — direct generation with `openai/gpt-image-2`.
13. `gpt_image_2_detail_board` — GPT Image 2 with the deterministic garment detail board.
14. `nano31_two_pass_repair` — full Nano Banana 2 direct candidate plus the same fixed garment-only repair pass.

Unsupported or provider-failed methods are recorded as failed and the queue continues. No failed method is silently replaced with a new method after scores are observed.

## Budget guard

- Read current key information from `GET /api/v1/key` using the existing repository secret.
- Derive remaining allowance from `limit_remaining`; when absent, calculate `limit - usage`. If neither is available, stop before spending.
- Check allowance before every generation and evaluation request.
- The hard floor is `$10.00`.
- Each request declares a conservative reserve. A request runs only when `remaining - reserve >= 10.00`.
- Near the floor, only the known low-cost Nano Banana 2 Lite direct method is eligible, with a `$0.06` reserve. This is intended to finish within roughly six cents above the floor without crossing it.
- Stop when no eligible next request can preserve the floor, the maximum request cap is reached, or a balance endpoint fails.
- Persist starting allowance, ending allowance, request costs, request counts, skipped requests, and stop reason.

## Search policy

- Primary ranking: mean valid frozen-rubric score across cases and replicates.
- Tie-breakers: print/logo, construction, and texture mean; then lower total cost; then lower latency.
- No best-of-N selection using the final evaluator. Every generated final candidate contributes to its method aggregate.
- Two-pass methods count both generation calls in method cost and latency.
- Existing D01-D03 data is development evidence only; H01/H02 are not rerun or used to tune this search.

## Outputs

- Per-request images and metadata in the workflow artifact.
- `results.csv` with method, case, replicate, model, pass count, frozen dimension scores, validity, cost, latency, and balance snapshots.
- `method_summary.csv` with aggregate scores/cost/latency and valid sample counts.
- `search_summary.json` with start/end allowance, stop reason, total spending, request counts, failures, and winner.
- Contact sheets for the leading methods and reviewer-neutral `review_scores.csv`.

## Scope

No UI, deployment, database, retries, evaluator tuning, holdout reruns, manual score fabrication, or automatic merging. The paid workflow is manual/reusable only and ordinary pushes or pull requests never spend credits.