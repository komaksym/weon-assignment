# D01 baseline execution record

## Status

`blocked`

The fixed D01 baseline reached the OpenRouter request exactly once, but the client received no response before its 180-second read timeout. Per the slice specification, no retry was attempted.

## Execution identity

- Workflow run: `30088159410`
- API attempt started: `2026-07-24T11:01:43Z`
- Command: `uv run weon-eval D01 --model bytedance-seed/seedream-4.5`
- Case: `D01`
- Model: `bytedance-seed/seedream-4.5`
- Prompt: `prompts/baseline.txt`
- Strategy: `baseline`
- Candidate count: `1`
- Live API requests made: `1`
- Additional cases executed: `none`
- Holdout cases executed: `none`

An earlier workflow invocation stopped during input validation before the API step because an assignment URL ending in `.jpg` returned PNG bytes. The local path was corrected to match the actual bytes; that failed precondition consumed no API request.

## Verified D01 inputs

The assignment-provided examples were downloaded, format-validated, and passed to the runner in this order:

| Role | Local path | Verified source | Dimensions |
| --- | --- | --- | --- |
| Model/person | `inputs/models/black-bodysuit-woman.png` | Model example 1: person wearing a black bodysuit | `3584 × 4800` |
| Environment | `inputs/environments/street.png` | European cobblestone street example | `1200 × 896` |
| Garment | `inputs/garments/shorts.png` | Garment example 1: olive technical shorts | `3470 × 3400` |

The garment reference visibly contains an olive base, darker contrast panels, two front buttons, belt loops, several zippered pockets, embroidered branding, and panel seams.

## Validation

All free gates passed before the live request:

- dependency sync: passed
- Ruff: passed
- strict mypy: passed
- tests: `13 passed`
- package build: passed
- paid-run case guard: passed
- repository secret guard: passed
- input preparation and media-format validation: passed

## Result

The request failed with the sanitized error:

```text
OpenRouter request failed: The read operation timed out
```

The error was emitted at `2026-07-24T11:04:44Z`, approximately `181.2` seconds after the generation command started.

No `image.png` or `metadata.json` was produced, so:

- the generated image could not be inspected;
- API-reported cost is unavailable;
- whether the provider billed the timed-out request cannot be confirmed from this run;
- runner-recorded latency is unavailable because persistence occurs only after a successful response.

## Manual inspection

Not performed. There is no generated artifact to compare with the person, environment, and garment references.

## Decision

`blocked`

Slice 2 stops here because its single allowed D01 API request has been used. Any retry or timeout-policy change is outside this slice and requires a separately approved follow-up after deciding how to handle the possibility that the timed-out request was processed or billed upstream.

The permanent manual `Run paid experiment` workflow remains available for later approved experiments. The one-time D01 trigger and diagnostic workflows were removed, and no D02, D03, H01, or H02 generation was attempted.
