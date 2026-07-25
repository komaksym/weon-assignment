from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text()
    if old not in text:
        raise SystemExit(f'Expected documentation block not found in {path}')
    file.write_text(text.replace(old, new, 1))


replace_once(
    'README.md',
    '''![Development comparison](submission/figures/development-comparison.jpg)

## What was tested''',
    '''![Development comparison](submission/figures/development-comparison.jpg)

The compact image above is report-only. Use the dedicated [author human-review protocol](submission/HUMAN_REVIEW.md) and its high-resolution sheets for actual garment-detail scoring. The sheets are prepared; numeric author ratings are pending and will be recorded separately.

## What was tested''',
)
replace_once(
    'README.md',
    '''A separate ChatGPT visual assessment was used as a sanity check. It was **not** independent human evaluation. The disagreement between visual errors and near-perfect automatic scores is itself a central result.''',
    '''A separate ChatGPT visual assessment was used as a sanity check. It was **not** independent human evaluation. A human sanity-check path is now prepared using the same six dimensions and full-resolution evidence; its pending ratings will be attributed to the assignment author rather than presented as independent review.''',
)
replace_once(
    'README.md',
    '''- [`REPORT.md`](REPORT.md) - final 10-minute report.
- [`submission/figures/`](submission/figures/) - durable before/after and holdout contact sheets.''',
    '''- [`REPORT.md`](REPORT.md) - final 10-minute report.
- [`submission/HUMAN_REVIEW.md`](submission/HUMAN_REVIEW.md) - author-review protocol and blank rating form.
- [`submission/review/`](submission/review/) - high-resolution D01-D03 and H01-H02 review sheets.
- [`submission/figures/`](submission/figures/) - compact report figures.''',
)
replace_once(
    'README.md',
    '''Raw assignment inputs and standalone generated outputs are not committed. Compact metrics, experiment records, and compressed contact sheets are durable in the repository.''',
    '''Raw assignment inputs and standalone generated outputs are not committed. Compact report figures and high-resolution composite review sheets preserve the durable visual evidence.''',
)
replace_once(
    'README.md',
    '''- No independent human reviewer participated.''',
    '''- No independent human reviewer participated. Author human ratings are prepared but not yet recorded.''',
)

replace_once(
    'REPORT.md',
    '''![Development comparison](submission/figures/development-comparison.jpg)

## 1. Failure-mode analysis''',
    '''![Development comparison](submission/figures/development-comparison.jpg)

The compact collage is a report summary, not a rating surface. Human scoring should use the separate [high-resolution author-review sheets](submission/HUMAN_REVIEW.md), which show each source garment, full generated candidate, and garment-region crop. The sheets are prepared; numeric author ratings are pending.

## 1. Failure-mode analysis''',
)
replace_once(
    'REPORT.md',
    '''A separate ChatGPT visual assessment reviewed committed contact sheets using the same concepts. This was an AI sanity check, **not independent human evaluation**.''',
    '''A separate ChatGPT visual assessment reviewed committed contact sheets using the same concepts. This was an AI sanity check, **not independent human evaluation**. A human sanity-check path is now prepared from the frozen full-resolution artifacts; its pending ratings will be explicitly attributed to the assignment author.''',
)
replace_once(
    'REPORT.md',
    '''The initial development matrix compared direct generation, structured prompting, and structured best-of-two. The blinded automatic mean tied at `0.8889` for all three. ChatGPT visual-assessment means were baseline `0.6833`, structured `0.6500`, and best-of-two `0.6500`. Best-of-two cost roughly twice as much and was much slower, so direct generation was frozen for the holdouts.

![H01 footwear holdout](submission/figures/H01-contact-sheet.jpg)''',
    '''The initial development matrix compared direct generation, structured prompting, and structured best-of-two. The blinded automatic mean tied at `0.8889` for all three. ChatGPT visual-assessment means were baseline `0.6833`, structured `0.6500`, and best-of-two `0.6500`. Best-of-two cost roughly twice as much and was much slower, so direct generation was frozen for the holdouts.

High-resolution development review sheets:

- [D01 technical shorts](submission/review/D01-human-review.png)
- [D02 low-top shoes](submission/review/D02-human-review.png)
- [D03 waxed jacket](submission/review/D03-human-review.png)

![H01 footwear holdout](submission/figures/H01-contact-sheet.jpg)

[Open the high-resolution H01 review sheet](submission/review/H01-human-review.png).''',
)
replace_once(
    'REPORT.md',
    '''![H02 shorts holdout](submission/figures/H02-contact-sheet.jpg)

| Holdout''',
    '''![H02 shorts holdout](submission/figures/H02-contact-sheet.jpg)

[Open the high-resolution H02 review sheet](submission/review/H02-human-review.png).

| Holdout''',
)
replace_once(
    'REPORT.md',
    '''H01's evaluator response incorrectly assigned `silhouette_length = -1` to footwear. The predeclared source mask required that dimension, so the raw response was retained but rejected from aggregation. H02 preserved the broad color, length, double-button waist, belt loops, and cargo layout, but branding, zipper placement, panel geometry, stitching, and technical-fabric texture remained approximate.

## 4. Practical conclusion and production design''',
    '''H01's evaluator response incorrectly assigned `silhouette_length = -1` to footwear. The predeclared source mask required that dimension, so the raw response was retained but rejected from aggregation. H02 preserved the broad color, length, double-button waist, belt loops, and cargo layout, but branding, zipper placement, panel geometry, stitching, and technical-fabric texture remained approximate.

### Author human review

The [author human-review protocol](submission/HUMAN_REVIEW.md) covers all nine initial development method outputs plus the two frozen holdouts using the same six dimensions. It deliberately excludes scene realism and asks the reviewer to score source-to-garment fidelity from the high-resolution detail crops.

The materials are complete, but the numeric ratings are not yet recorded. Until they are supplied, this report makes no human-score claim. When added, they will remain a separate attributed evidence path and will not replace or retune the frozen automatic or ChatGPT results.

## 4. Practical conclusion and production design''',
)
replace_once(
    'REPORT.md',
    '''This is a focused exploration, not a large benchmark. It uses five distinct cases with repeated development samples. No independent human reviewer participated. ChatGPT performed the second visual-assessment path and assisted with implementation, orchestration, analysis, and writing. Image outputs came from the tested generation models; automatic scores and best-of-two selection used GPT-4.1 Mini.''',
    '''This is a focused exploration, not a large benchmark. It uses five distinct cases with repeated development samples. No independent human reviewer participated. High-resolution author-review materials are prepared, but their ratings are pending. ChatGPT performed the existing visual-assessment path and assisted with implementation, orchestration, analysis, evidence layout, and writing. Image outputs came from the tested generation models; automatic scores and best-of-two selection used GPT-4.1 Mini.''',
)

replace_once(
    'PLANS.md',
    '''**Summary:** The four-slice assignment and the follow-up development-only extension are complete. No tested method reliably improved on direct generation, the automatic evaluator saturated before exact product fidelity, and paid exploration stopped with direct generation retained as the operational baseline.''',
    '''**Summary:** The four-slice assignment and the follow-up development-only extension are complete. No tested method reliably improved on direct generation, the automatic evaluator saturated before exact product fidelity, and paid exploration stopped with direct generation retained as the operational baseline. High-resolution author-review materials are prepared; numeric ratings are pending.''',
)
replace_once(
    'PLANS.md',
    '''    P --> D[Stop: baseline not beaten ✓]
```''',
    '''    P --> D[Stop: baseline not beaten ✓]
    D --> H[Author review sheets ready; ratings pending]
```''',
)
replace_once(
    'PLANS.md',
    '''## Evaluation integrity and provenance''',
    '''## Author human review

**Status:** high-resolution evidence and rating protocol complete; ratings pending.

**Scope:** D01-D03 baseline, structured, and best-of-two outputs plus the frozen H01-H02 baseline outputs. The reviewer will use the same six dimensions and will be identified as the assignment author, not an independent rater.

**Evidence:** The review sheets were rebuilt from the original full-resolution development run `30102014361` and holdout run `30113526488`. No model call, output, score, cost, or experiment decision changed.

**Next step:** Record the raw author ratings, method means, holdout results, and qualitative conclusions without replacing or retuning the frozen automatic and ChatGPT evidence.

## Evaluation integrity and provenance''',
)
replace_once(
    'PLANS.md',
    '''- ChatGPT produced the visual-assessment scores from committed contact sheets. No independent human evaluator participated; this is an explicit limitation of the evidence.''',
    '''- ChatGPT produced the existing visual-assessment scores from committed contact sheets. No independent human evaluator participated; this remains an explicit limitation.
- Author human ratings are pending and will be stored as a separate attributed evidence path.''',
)
replace_once(
    'PLANS.md',
    '''- Compressed crop-enhanced contact sheets remain as durable submission visual evidence.''',
    '''- Compact report figures and high-resolution composite review sheets preserve durable visual evidence.''',
)
