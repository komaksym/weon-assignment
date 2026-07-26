# Human Review Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the six-dimension reviewer with an 11-decision, evidence-first
desktop workflow.

**Architecture:** Keep the existing dependency-free local server. Simplify the
Python review document and summaries to one score per output, then rebuild the
single static page around large comparison panes and immediate autosave.

**Tech Stack:** Python 3.12+, `http.server`, JSON, Pillow, vanilla
HTML/CSS/JavaScript, pytest, Ruff, strict mypy.

## Global Constraints

- Exactly 11 scored outputs.
- Scores are exactly `1`, `0.5`, or `0`.
- Development methods stay blinded as A/B/C in the scoring screen.
- Holdouts remain separate from development means.
- Desktop only; no new dependency or paid request.
- Existing unreliable ratings must not pre-fill the authoritative pass.

---

### Task 1: Simplify the review contract

**Files:**
- Modify: `src/weon_eval/human_review/model.py`
- Modify: `src/weon_eval/human_review/server.py`
- Modify: `tests/test_human_review.py`

**Interfaces:**
- Produces: one `score` plus optional `note` per review item.
- Produces: development means/ranking and separate holdout results.

- [ ] Write failing tests for `1/0.5/0` validation, an empty document,
  development means, ties, holdout separation, and JSON/CSV/Markdown exports.
- [ ] Run `uv run pytest tests/test_human_review.py -q` and confirm the new tests
  fail against the six-dimension contract.
- [ ] Implement the smallest model/server changes that pass those tests.
- [ ] Re-run the focused tests.

### Task 2: Build the evidence-first desktop screen

**Files:**
- Modify: `src/weon_eval/human_review/static/index.html`
- Modify: `src/weon_eval/human_review/static/app.js`
- Modify: `src/weon_eval/human_review/static/styles.css`
- Modify if required: `src/weon_eval/human_review/server.py`

**Interfaces:**
- Consumes: `/api/config`, `/api/review`, evidence routes, and export routes.
- Produces: one-case comparison, 11 ratings, autosave/resume, keyboard
  navigation, progress, enlargement/zoom, and final summary.

- [ ] Add HTTP/UI-state tests for save/resume and the public 11-item manifest.
- [ ] Implement source/candidate comparison panes and readable evidence modes.
- [ ] Implement three score buttons, optional note, autosave-and-advance,
  previous/next, keyboard shortcuts, and summary/export controls.
- [ ] Run focused Python tests and
  `node --check src/weon_eval/human_review/static/app.js`.

### Task 3: Verify the disposable reviewer end-to-end

**Files:**
- Modify: `README.md`
- Modify: `submission/HUMAN_REVIEW.md`
- Create: browser screenshot in a temporary QA directory.

**Interfaces:**
- Produces: concise launch and scoring instructions.

- [ ] Start the local server with an empty temporary ratings file.
- [ ] In a desktop browser, verify readable evidence, all 11 decisions,
  autosave, reload/resume, navigation, means/ranking, holdout separation, and
  JSON/CSV/Markdown export.
- [ ] Inspect the final screenshot at full resolution.
- [ ] Run `uv run ruff check .`, `uv run mypy src`, `uv run pytest`, and
  `uv build`; fix any failures.
