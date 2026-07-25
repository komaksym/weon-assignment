# High-resolution visual audit

## Disclosure

This is an **AI-assisted visual audit**, not a human review. It was performed from the frozen full-resolution development and holdout artifacts using the same six-dimension rubric as the planned author review. It does not replace independent human evaluation and does not modify the frozen automatic scores.

The audit deliberately re-checked the earlier negative narrative rather than assuming it was correct. The main correction is that **the shorts cases are much stronger than the earlier report language implied**. The clearest residual failures are concentrated in footwear branding/panel geometry and jacket construction.

## Rubric

Scores use the frozen scale:

- `1` — preserved with no meaningful visible discrepancy;
- `0.5` — recognizable and substantially preserved, but visibly changed;
- `0` — missing, hallucinated, or clearly wrong;
- `-1` — genuinely not applicable in the source garment.

The row mean excludes `-1`.

## Ratings

| Case | Method | Color | Print/logo | Silhouette/length | Construction | Texture/material | Presence | Mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D01 | baseline | 1 | 0.5 | 1 | 0.5 | 1 | 1 | **0.8333** |
| D01 | structured | 1 | 0.5 | 1 | 0.5 | 1 | 1 | **0.8333** |
| D01 | best-of-two | 1 | 0.5 | 1 | 0.5 | 1 | 1 | **0.8333** |
| D02 | baseline | 1 | 0 | 0.5 | 0.5 | 0.5 | 1 | **0.5833** |
| D02 | structured | 1 | 0 | 0.5 | 0.5 | 0.5 | 1 | **0.5833** |
| D02 | best-of-two | 1 | 0 | 0.5 | 0.5 | 0.5 | 1 | **0.5833** |
| D03 | baseline | 0.5 | -1 | 1 | 0.5 | 0.5 | 1 | **0.7000** |
| D03 | structured | 0.5 | -1 | 1 | 0.5 | 0.5 | 1 | **0.7000** |
| D03 | best-of-two | 0.5 | -1 | 1 | 0.5 | 0.5 | 1 | **0.7000** |
| H01 | frozen baseline | 1 | 0 | 0.5 | 0.5 | 0.5 | 1 | **0.5833** |
| H02 | frozen baseline | 1 | 0.5 | 1 | 0.5 | 1 | 1 | **0.8333** |

Development method means:

- baseline: **0.7056**;
- structured: **0.7056**;
- best-of-two: **0.7056**.

The three development method means tie in this audit. For D01-D03, the committed best-of-two output is the selected structured-A image, so the structured and best-of-two rating surfaces are identical for those rows.

## Case notes

### D01 — technical shorts

The garment is a strong match. The olive palette, above-knee silhouette, double-button waist, dark upper pocket panels, thigh zipper layout, lower reinforcement panels, and technical-fabric appearance are all recognizably preserved.

The remaining weaknesses are identity-level rather than category-level: the embroidered brand mark is only an approximate/unreadable mark at inspection scale, and small construction features such as the D-ring and exact loop/pocket geometry are not faithfully reproduced. That is why print/logo and construction receive `0.5` rather than `1`.

**Verdict:** much stronger than the earlier automatic/visual narrative suggested, but not exact at branding and micro-construction level.

### D02 — low-top shoes

The brown/tan palette and overall low-top sneaker identity are preserved, but this is where exact product fidelity breaks most clearly.

The source has visible gold `ARIGATO` side branding and a specific combination of brown and tan overlays. In the generated outputs the visible outer side does not preserve legible `ARIGATO` branding, the tan/brown toe and side-panel boundaries change shape, and the toe/sole proportions are only approximate. The material still reads as a leather/suede mix, but the material boundaries drift with the panel geometry.

**Verdict:** same product family/style, not a reliable exact-product reproduction.

### D03 — waxed jacket

The overall dark-green field-jacket identity, hip length, and general silhouette are preserved well.

The exact construction is not. The source has a distinct dark-brown corduroy collar, concealed front closure, and specific large lower-pocket construction. The generated versions simplify or change the collar color/material, expose buttons/zipper or alter the placket, and change the lower-pocket construction. The body still reads as waxed/coated fabric, but the material specificity and collar treatment are only partial.

`print_logo = -1` because there is no applicable exterior print/logo in the source.

**Verdict:** visually convincing as the same kind of jacket, but not exact enough at collar, closure, and pocket construction.

### H01 — footwear holdout

This repeats the D02 failure pattern. The brown/tan palette is preserved, but the source `ARIGATO` branding is not reliably legible on the generated shoe, the toe/side overlay geometry changes, and the low-top/sole proportions are approximate. Leather/suede character remains recognizable while the exact boundaries drift.

**Verdict:** the holdout confirms that footwear identity is the weakest tested category.

### H02 — shorts holdout

This is another strong match. The olive palette, double-button waist, dark upper panels, thigh zips, hem treatment, length, and overall technical-short construction are all close to the source.

The remaining differences are small but identity-relevant: branding and asymmetric micro-details are not exact, some side-specific markings appear moved or mirrored, and the D-ring-level construction is not faithfully preserved.

**Verdict:** strong visual preservation, but still not a trustworthy exact SKU reproduction for brand-critical use.

## Overall judgments

1. **Did structured prompting consistently outperform baseline?** No.
   - The high-resolution visual scores tie across D01-D03. No repeatable qualitative advantage is visible.

2. **Did best-of-two consistently outperform baseline?** No.
   - It ties the baseline visually in this matrix while costing more. In these development artifacts, best-of-two selected the structured-A image, so there is no separate visual improvement to score.

3. **Are any outputs sufficiently faithful for brand-critical catalog use?** No.
   - D01 and H02 are strong enough to demonstrate useful garment preservation, but branding and micro-construction are still not exact. D02/H01 and D03 show larger identity-level drift.

4. **Did automatic-perfect or near-perfect results contain obvious garment errors?** Yes.
   - The strongest examples are missing/unreadable footwear branding and changed shoe panel/sole geometry, plus changed jacket collar, closure, and pocket construction.

5. **Overall preferred development method:** Baseline.
   - The visual audit finds no method-level gain over baseline, while best-of-two adds cost and latency. The direct baseline therefore remains the best operational choice on the evidence available.

## Interpretation

The strongest honest conclusion is not that the baseline is poor. It is that **the baseline is already very good on some garments, especially the shorts, and the tested complexity did not improve it**.

The benchmark is also small and uneven in difficulty. D01/H02 may be relatively easy for the generator, while D02/H01 expose identity-critical footwear failures and D03 exposes construction drift. A larger benchmark would be needed to estimate the actual pass rate for exact product preservation.
