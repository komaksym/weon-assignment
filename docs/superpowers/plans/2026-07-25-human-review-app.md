# Human Review App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dependency-free local browser evaluator that reduces the author human review to one-click presets plus exceptional corrections and exports the complete result.

**Architecture:** A standard-library HTTP server serves a static single-page UI, the committed review sheets, and a small JSON API. A pure Python model module owns the frozen rubric, blind manifest, validation, aggregation, and exports; the server atomically persists partial progress.

**Tech Stack:** Python 3.12+, `http.server`, dataclasses, JSON, vanilla HTML/CSS/JavaScript, pytest, Ruff, strict mypy, Hatchling.

## Global Constraints

- Add no production dependency.
- Preserve dimensions `color`, `print_logo`, `silhouette_length`, `construction_details`, `texture_material`, and `garment_presence`.
- Preserve score values `1`, `0.5`, `0`, and `-1` only for genuinely inapplicable source dimensions.
- Keep holdout summaries separate from development method means.
- Auto-save to `submission/human-review-ratings.json` by default.
- Serve only on `127.0.0.1` by default.
- Never perform a paid model request.

---

### Task 1: Frozen review model and exports

**Files:**
- Create: `src/weon_eval/human_review/__init__.py`
- Create: `src/weon_eval/human_review/model.py`
- Test: `tests/test_human_review.py`

**Interfaces:**
- Produces: `public_config() -> dict[str, object]`, `validate_document(value: object) -> ReviewDocument`, `summarize(document: ReviewDocument) -> dict[str, object]`, `render_markdown(document: ReviewDocument) -> str`, and `render_csv(document: ReviewDocument) -> str`.

- [ ] Write failing tests for N/A-aware means, invalid scores, blind config, method means, holdout separation, Markdown, and CSV.
- [ ] Run `uv run pytest tests/test_human_review.py -q` and verify failures are caused by the missing module.
- [ ] Implement the immutable manifest, typed document validation, aggregation, and export functions.
- [ ] Run the focused tests and verify they pass.

### Task 2: Atomic storage and local HTTP API

**Files:**
- Create: `src/weon_eval/human_review/server.py`
- Test: `tests/test_human_review.py`

**Interfaces:**
- Consumes: all model functions from Task 1.
- Produces: `ReviewStore`, `make_handler(...)`, and `create_server(...)`.

- [ ] Add failing tests for an empty load, atomic save/load, config GET, review PUT/GET, evidence GET, and Markdown export GET.
- [ ] Run the focused tests and verify expected failures.
- [ ] Implement storage and HTTP routes with JSON error responses and path traversal protection.
- [ ] Run the focused tests and verify they pass.

### Task 3: Fast single-page evaluator

**Files:**
- Create: `src/weon_eval/human_review/static/index.html`
- Create: `src/weon_eval/human_review/static/app.js`
- Create: `src/weon_eval/human_review/static/styles.css`

**Interfaces:**
- Consumes: `/api/config`, `/api/review`, `/api/export/*`, and `/evidence/{case_id}.png`.
- Produces: one-target-at-a-time scoring, one-click preset-and-next, corrections, issue tags, notes, progress, resume, summary, and exports.

- [ ] Implement semantic static markup with accessible labels and no framework.
- [ ] Implement state loading, debounced auto-save, presets, score controls, issue tags, navigation, summary, and exports.
- [ ] Implement responsive styling, visible focus states, high-resolution evidence zoom, and reduced-motion support.
- [ ] Run `node --check src/weon_eval/human_review/static/app.js`.

### Task 4: CLI and repository documentation

**Files:**
- Create: `src/weon_eval/human_review_cli.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `submission/HUMAN_REVIEW.md`

**Interfaces:**
- Consumes: `create_server(...)`.
- Produces: `uv run weon-human-review` with `--host`, `--port`, `--data`, and `--no-browser`.

- [ ] Add failing parser/root-discovery tests.
- [ ] Implement CLI, browser launch, and clean shutdown.
- [ ] Add the script entry point and concise run/resume/export documentation.
- [ ] Run focused tests.

### Task 5: End-to-end verification and PR evidence

**Files:**
- Create: `submission/figures/human-review-app.jpg`
- Modify: PR description only for the DAG and screenshot.

- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run mypy src`.
- [ ] Run `uv run pytest`.
- [ ] Run `uv build`.
- [ ] Start the server against test evidence and exercise preset, correction, reload, summary, and export with Playwright Chromium.
- [ ] Capture desktop and mobile screenshots; keep the desktop screenshot in the repository.
- [ ] Open a PR with a small DAG, screenshot, validation results, and AI disclosure.
