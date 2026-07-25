# Author human-review protocol

## Status and disclosure

The crop-first review sheets are prepared. Numeric ratings are **pending**.

The reviewer will be **Maksym Koval, the assignment author**. This satisfies the task's human sanity-check requirement, but it is not independent or multi-rater human evaluation. The raw ratings and calculated summaries will be committed after the reviewer submits the completed form.

No image was regenerated for this review. The sheets reuse the frozen outputs from:

- development workflow run `30102014361`, artifact `development-matrix-30102014361`;
- holdout workflow run `30113526488`, artifact `frozen-holdouts-30113526488`.

The revised sheets change presentation only. They do not change prompts, candidates, automatic scores, costs, or the frozen baseline decision. The garment crops come from the original full-resolution outputs. A small display-only clarity pass was applied equally to every crop; no relighting, recoloring, segmentation, or content generation was used.

## Review sheets

Open each PNG at full resolution before scoring:

- [D01 — technical shorts](review/D01-human-review.png)
- [D02 — low-top shoes](review/D02-human-review.png)
- [D03 — waxed jacket](review/D03-human-review.png)
- [H01 — footwear holdout](review/H01-human-review.png)
- [H02 — shorts holdout](review/H02-human-review.png)

Do not consult the existing automatic or ChatGPT visual scores until all ratings are complete.

## Rating order and confound control

The methods generated separate full scenes, so pose, stance, facial expression, and lighting can differ. Those differences must not become a proxy for garment quality.

Use this fixed order for every output:

1. **Primary garment crop:** assign the garment-fidelity scores from this crop first.
2. **Detail zoom:** inspect logos, text, closures, buttons, pockets, seams, panels, perforation, stitching, and material boundaries.
3. **Small context image:** use only for overall silhouette/length and garment presence, or when a crop hides relevant context.

Ignore these unless they prevent garment inspection:

- model pose or stance;
- facial expression or body presentation;
- how flattering or aesthetically strong the person render looks;
- background realism or composition;
- scene lighting as an aesthetic quality.

Lighting can still cause real visible garment-color drift. Score the visible garment color against the source, but do not reward a method merely because its model or scene is better lit.

## Scoring rubric

Score each dimension with exactly one value:

| Score | Meaning |
| ---: | --- |
| `1` | Preserved: no meaningful visible discrepancy |
| `0.5` | Partially preserved: recognizable, but visibly changed |
| `0` | Drifted, missing, hallucinated, or unacceptable |
| `-1` | Genuinely not applicable in the source garment |

Use `-1` only when the source itself makes the dimension inapplicable. Footwear silhouette is applicable.

Rate these six dimensions:

1. **Color** — global and local garment colors.
2. **Print/logo** — text, branding, graphics, placement, and legibility.
3. **Silhouette/length** — proportions, outline, garment length, collar or toe shape, and sole thickness.
4. **Construction details** — pockets, buttons, zippers, seams, panels, closures, and stitching.
5. **Texture/material** — leather, suede, technical fabric, waxed coating, perforation, and material boundaries.
6. **Garment presence** — the intended garment is visibly present and worn or positioned appropriately.

The row mean excludes dimensions scored `-1`.

## Case-specific inspection points

- **D01 and H02 shorts:** branding, double-button waist, belt loops, zipper placement, pocket count and geometry, dark reinforcement panels, stitching, hem, length, and technical-fabric appearance.
- **D02 and H01 shoes:** exact `ARIGATO` branding, toe-panel geometry, sole shape and thickness, perforation, leather/suede boundaries, low-top silhouette, and brown/orange color placement.
- **D03 jacket:** collar proportions, front closure, pocket count and placement, seams and panels, jacket length, dark-green color, and waxed-material appearance.

## Rating form

Copy this form, fill every numeric field, and add one concise visible issue per row.

```text
Rater: Maksym Koval
Review date: YYYY-MM-DD
Review type: Author human review

D01 — baseline
Color:
Print/logo:
Silhouette/length:
Construction details:
Texture/material:
Garment presence:
Most important visible issue:

D01 — structured
Color:
Print/logo:
Silhouette/length:
Construction details:
Texture/material:
Garment presence:
Most important visible issue:

D01 — best-of-two
Color:
Print/logo:
Silhouette/length:
Construction details:
Texture/material:
Garment presence:
Most important visible issue:

D02 — baseline
Color:
Print/logo:
Silhouette/length:
Construction details:
Texture/material:
Garment presence:
Most important visible issue:

D02 — structured
Color:
Print/logo:
Silhouette/length:
Construction details:
Texture/material:
Garment presence:
Most important visible issue:

D02 — best-of-two
Color:
Print/logo:
Silhouette/length:
Construction details:
Texture/material:
Garment presence:
Most important visible issue:

D03 — baseline
Color:
Print/logo:
Silhouette/length:
Construction details:
Texture/material:
Garment presence:
Most important visible issue:

D03 — structured
Color:
Print/logo:
Silhouette/length:
Construction details:
Texture/material:
Garment presence:
Most important visible issue:

D03 — best-of-two
Color:
Print/logo:
Silhouette/length:
Construction details:
Texture/material:
Garment presence:
Most important visible issue:

H01 — frozen baseline
Color:
Print/logo:
Silhouette/length:
Construction details:
Texture/material:
Garment presence:
Most important visible issue:

H02 — frozen baseline
Color:
Print/logo:
Silhouette/length:
Construction details:
Texture/material:
Garment presence:
Most important visible issue:

Overall questions

1. Did structured prompting consistently outperform baseline? Yes / No / Unclear
Reason:

2. Did best-of-two consistently outperform baseline? Yes / No / Unclear
Reason:

3. Are any outputs sufficiently faithful for brand-critical catalog use? Yes / No
Reason:

4. Did any automatic-perfect or near-perfect result contain obvious garment errors? Yes / No
Examples:

5. Overall preferred development method:
Baseline / Structured / Best-of-two / No reliable winner
Reason:
```

## Recording the result

After the completed form is submitted, preserve:

- the raw per-row ratings;
- per-output means;
- development method means;
- holdout means reported separately;
- the qualitative answers and reviewer attribution;
- comparison against the frozen automatic and ChatGPT visual scores.

Human ratings must not replace, retune, or silently modify the frozen automatic evidence.
