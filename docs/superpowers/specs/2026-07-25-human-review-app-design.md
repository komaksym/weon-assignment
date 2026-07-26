# Disposable Human Review Design

## Goal

Make the assignment's human sanity check fast and reliable by showing garment
evidence at a genuinely readable size and requiring only one decision per
generated output.

## Review contract

- Review 11 outputs: D01-D03 × A/B/C, then H01-H02.
- Record one overall garment-fidelity score per output:
  - `1` — Preserved
  - `0.5` — Noticeable drift
  - `0` — Major failure
- Permit one optional short note.
- Keep development methods blinded as A/B/C while scoring.
- Compute each method's mean over D01-D03 and derive its ranking automatically;
  ties are valid.
- Report H01-H02 separately from the development comparison.
- Start the authoritative pass empty. Preserve any earlier ratings as an
  archive, never as pre-filled answers.

The score concerns only visible, expected garment evidence: color, logos/text,
silhouette, construction, texture, and presence. It does not judge model
identity, pose, background, or general image aesthetics except where they make
the garment impossible to assess.

## Reviewer experience

The desktop page shows one case at a time. Development cases show the source
garment and candidates A/B/C together; holdouts show the source and one output.
Each pane prioritizes a large, high-resolution garment crop. The reviewer can
switch to detail or full-scene evidence, click a pane to enlarge it, and use
zoom/pan without losing the comparison.

The three score buttons sit directly below the evidence and use both plain
language and numeric values. Selecting a score saves immediately and advances
to the next unanswered output. Previous/next controls, keyboard shortcuts,
progress, save status, and resume are always visible. Instructions remain short
and concrete on the screen.

## Persistence and outputs

The existing standard-library local server remains the delivery mechanism.
Ratings persist atomically to JSON and can be exported as JSON, CSV, and
Markdown. Exports include raw decisions, development means/ranking, and
separate holdout scores.

The reviewer UI and generated viewing crops are disposable local tooling. The
authoritative ratings and exports are the durable result.

## Scope

- Reuse the existing Python server and vanilla HTML/CSS/JavaScript.
- Desktop only.
- Add no React app, database, deployment, authentication, production
  dependency, paid API request, or mobile layout.
- Do not rewrite the assignment narrative automatically.

## Verification

- Unit tests cover valid scores, empty-state behavior, development means, ties,
  holdout separation, and exports.
- HTTP tests cover save/resume, evidence, and export routes.
- Browser QA covers all 11 decisions, readable evidence, autosave, reload,
  navigation, summary, and export.
- Ruff, strict mypy, pytest, JavaScript syntax check, and package build pass.
