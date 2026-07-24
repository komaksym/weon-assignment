# D01 baseline execution record

## Status

`complete — proceed to slice 3`

The final operational D01 baseline completed successfully with Nano Banana 2 Lite through the permanent paid workflow. The generated image is mechanically valid, opens successfully, and provides usable baseline evidence despite visible garment-detail drift.

## Execution identity

- Workflow run: `30092628023`
- Artifact: `experiment-D01-30092628023`
- Artifact created: `2026-07-24T12:19:19Z`
- Command: `uv run weon-eval D01 --model google/gemini-3.1-flash-lite-image`
- Case: `D01`
- Split: `development`
- Model: `google/gemini-3.1-flash-lite-image`
- Prompt: `prompts/baseline.txt`
- Strategy: `baseline`
- Candidate count: `1`
- Final operational requests: `1`
- Additional development cases executed: `none`
- Holdout cases executed: `none`

The initially planned Seedream 4.5 call had previously timed out without returning an artifact. A separately isolated diagnostic demonstrated that Nano Banana 2 Lite could process the same case after compact preprocessing, so it was selected as the operational baseline. Diagnostic branches and one-use callers were not merged into the slice branch.

## Configuration

- Requested resolution: `1K`
- Requested aspect ratio: `3:4`
- Automatic retries: `0`
- Output file: `image.jpg`
- Output media type: `image/jpeg`
- Output dimensions: `896 × 1200`
- Measured generation latency: `7.076151859 s`
- API-reported cost: `$0.03497325`

## Reference preprocessing

The original ignored inputs remained unchanged. Each reference was EXIF-oriented, resized in memory to a maximum dimension of 1024 pixels, composited onto white when needed, and encoded as JPEG quality 85.

| Role | Path | Original | Prepared | Prepared bytes |
| --- | --- | ---: | ---: | ---: |
| Model/person | `inputs/models/black-bodysuit-woman.png` | `3584 × 4800` | `765 × 1024` | `40,204` |
| Environment | `inputs/environments/street.png` | `1200 × 896` | `1024 × 765` | `184,718` |
| Garment | `inputs/garments/shorts.png` | `3470 × 3400` | `1024 × 1003` | `136,329` |

The references were passed in model/person, environment, garment order.

## Validation

All free gates passed before the paid request:

- dependency sync: passed
- Ruff: passed
- strict mypy: passed
- tests: `14 passed`
- package build: passed
- paid-run case guard: passed
- repository-secret guard: passed
- selected-case download and source-format validation: passed
- deterministic reference compaction: passed

## Manual inspection

### Composition mechanics

| Dimension | Label | Evidence |
| --- | --- | --- |
| Intended person | `preserved` | Face, hair, black bodysuit, gold collar detail, shoes, and overall identity are strongly recognizable. |
| Street environment | `preserved` | The wet cobblestone old-town street and surrounding architecture are clearly retained. |
| Garment presence | `preserved` | The olive shorts are worn naturally on the person rather than pasted into the scene. |

### Garment consistency

| Dimension | Label | Evidence |
| --- | --- | --- |
| Olive color | `preserved` | The dominant olive-green tone closely matches the packshot. |
| Silhouette and length | `partially preserved` | Knee-length technical-shorts proportions are retained, but the exact cut is simplified. |
| Dark contrast panels | `partially preserved` | Darker sections remain visible, but their shapes and placement differ from the packshot. |
| Waistband and belt loops | `preserved` | The waistband and visible belt-loop construction are retained. |
| Two-button closure | `partially preserved` | Two dark closure elements are visible, but the construction is simplified. |
| Zipper and pocket layout | `partially preserved` | Technical pockets and zipper-like details remain, but placement, count, and geometry drift. |
| Embroidery or logo | `drifted` | The visible packshot branding is missing from the generated garment. |
| Seams and panel geometry | `partially preserved` | Panelled construction remains, but exact seams and panel boundaries are redesigned. |
| Material appearance | `partially preserved` | The result reads as technical woven fabric, but fine texture is not faithfully reproduced. |
| Hallucinated details | `partially preserved` | No severe extra garment is introduced, but simplified pockets and paneling replace exact source details. |

## Decision

`proceed to slice 3`

The artifact is mechanically valid, exactly `3:4`, inexpensive, fast, and sufficiently documented for a development-set baseline comparison. Missing branding and structural drift are useful baseline failures for slice 3 and later improvement strategies; they do not justify resampling this case.

The permanent manual `Run paid experiment` workflow remains available. The one-use execution PR was closed without merging, generated files remain outside Git history, and no D02, D03, H01, or H02 generation was attempted.
