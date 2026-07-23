# D01 baseline execution record

## Status

`blocked`

Slice 2 did not send a live request because a required precondition failed: `OPENROUTER_API_KEY` is not available in the execution environment or as a repository secret. The assignment email confirms that the key was shared separately over chat, so it cannot be recovered from the connected email or Drive sources.

## Execution identity

- Checked at: `2026-07-23T01:36:16Z`
- Intended command: `uv run weon-eval D01`
- Case: `D01`
- Model: `bytedance-seed/seedream-4.5`
- Prompt: `prompts/baseline.txt`
- Strategy: `baseline`
- Live requests made: `0`
- Credits spent: `$0.00`
- Holdout cases executed: `none`

## Verified D01 inputs

The assignment-provided examples were fetched into a temporary private CI artifact, opened, and matched to the case definition:

| Role | Expected local path | Verified source | Dimensions |
| --- | --- | --- | --- |
| Model/person | `inputs/models/black-bodysuit-woman.png` | Model example 1: person wearing a black bodysuit | `3584 × 4800` |
| Environment | `inputs/environments/street.png` | European cobblestone street example | `1200 × 896` |
| Garment | `inputs/garments/shorts.png` | Garment example 1: olive technical shorts | `3470 × 3400` |

The garment has visible details suitable for later consistency inspection: olive color, darker contrast panels, two front buttons, belt loops, multiple zippered pockets, embroidered branding, and panel seams.

The temporary diagnostic workflow and downloaded images are not part of the branch history.

## Validation

The normal repository gates passed before the blocked execution decision:

- dependency sync: passed
- Ruff: passed
- strict mypy: passed
- tests: passed
- package build: passed

## Result

No `image.png` or `metadata.json` exists because no API request was sent. There is therefore no garment-consistency observation, cost measurement, or latency measurement to report.

## Decision

`blocked`

The next execution attempt must use the existing one-call command after `OPENROUTER_API_KEY` is made available to the execution environment. It must not alter the prompt, model, case, reference order, resolution, aspect ratio, or candidate count, and it must not execute any holdout case.
