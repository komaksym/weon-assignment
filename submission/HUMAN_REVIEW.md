# Author human-review protocol

## Status and disclosure

The crop-first review sheets, local rating app, and attributed author ratings are complete.

Recorded evidence:

- [human-review-ratings.json](human-review-ratings.json) — authoritative saved review document;
- [human-review-ratings.csv](human-review-ratings.csv) — portable per-output ratings;
- [HUMAN_REVIEW_RESULTS.md](HUMAN_REVIEW_RESULTS.md) — readable result summary.

The reviewer will be **Maksym Koval, the assignment author**. This satisfies the task's human sanity-check requirement, but it is not independent or multi-rater human evaluation. The raw ratings and calculated summaries will be committed after the reviewer completes the app.

No image was regenerated for this review. The sheets reuse the frozen outputs from:

- development workflow run `30102014361`, artifact `development-matrix-30102014361`;
- holdout workflow run `30113526488`, artifact `frozen-holdouts-30113526488`.

The revised sheets change presentation only. They do not change prompts, candidates, automatic scores, costs, or the frozen baseline decision. The garment crops come from the original full-resolution outputs. A small display-only clarity pass was applied equally to every crop; no relighting, recoloring, segmentation, or content generation was used.

## Run the evaluator

From the repository root:

```bash
uv sync --dev
uv run weon-human-review
```

The command opens a local browser app at `http://127.0.0.1:8765`.

The fastest valid workflow is:

1. Compare the source and all candidates on the same case screen.
2. Start with **Garment crop**; use **Detail zoom** for logos/construction and **Full scene** only for silhouette or visibility.
3. Give each output one overall score: **1 Preserved**, **0.5 Noticeable drift**, or **0 Major failure**.
4. Add a short note only when it helps explain a failure.
5. Continue through D01-D03 and H01-H02, then export the results.

This is 11 decisions total: three candidates for each development case and one output for each holdout. Click any image to open the high-resolution full-screen inspector. Keyboard shortcuts `1`, `2`, and `3` apply the three scores to the highlighted candidate.

Every rated output auto-saves to `submission/human-review-ratings.json`. Restarting the command resumes at the first incomplete case. If an older six-dimension ratings file exists, the app preserves it as `submission/human-review-ratings.legacy-v1.json` and starts a clean authoritative pass. The summary page exports JSON, CSV, and submission-ready Markdown.

Useful options:

```bash
uv run weon-human-review --no-browser
uv run weon-human-review --port 9000
uv run weon-human-review --data /tmp/human-review-ratings.json
```

## Review sheets

The app serves these committed PNGs at full resolution:

- [D01 — technical shorts](review/D01-human-review.png)
- [D02 — low-top shoes](review/D02-human-review.png)
- [D03 — waxed jacket](review/D03-human-review.png)
- [H01 — footwear holdout](review/H01-human-review.png)
- [H02 — shorts holdout](review/H02-human-review.png)

For the local review session, the app prefers the untouched garment packshots in
`inputs/garments/` and the untouched generated files in `outputs/human-review/`
for references and full scenes. Both are ignored local evidence caches; if a
file is absent, the app falls back to the committed review sheet. Fit mode never
enlarges an image beyond its available pixels.

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

Give each generated output exactly one overall visible garment-fidelity score:

| Score | Meaning |
| ---: | --- |
| `1` | **Preserved:** visible identity details remain faithful |
| `0.5` | **Noticeable drift:** recognizable, but important visible details changed |
| `0` | **Major failure:** garment identity is missing, replaced, or materially incorrect |

Consider color, print/logo, silhouette/length, construction, material, and garment presence together. Score only details expected to be visible. If the composition hides an important detail, do not invent evidence; judge what is visible and use the optional note when the visibility failure matters.

## Case-specific inspection points

- **D01 and H02 shorts:** branding, double-button waist, belt loops, zipper placement, pocket count and geometry, dark reinforcement panels, stitching, hem, length, and technical-fabric appearance.
- **D02 and H01 shoes:** exact `ARIGATO` branding, toe-panel geometry, sole shape and thickness, perforation, leather/suede boundaries, low-top silhouette, and brown/orange color placement.
- **D03 jacket:** collar proportions, front closure, pocket count and placement, seams and panels, jacket length, dark-green color, and waxed-material appearance.

## Recording the result

The app preserves:

- the raw per-output ratings;
- development method means;
- an automatically derived development ranking, with ties preserved;
- holdout scores reported separately;
- optional notes and reviewer attribution;
- JSON, CSV, and Markdown exports.

Human ratings must not replace, retune, or silently modify the frozen automatic evidence.
