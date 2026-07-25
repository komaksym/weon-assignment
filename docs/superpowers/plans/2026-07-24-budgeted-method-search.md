# Budgeted Method Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and execute a frozen-evaluation, balance-guarded search over predeclared garment-consistency methods until the OpenRouter key reaches the `$10.00` floor.

**Architecture:** Add a focused `budget_search` module that owns method definitions, deterministic reference boards, two-pass execution, frozen single-candidate scoring, balance checks, aggregation, and artifacts. Reuse the existing case loader, image boundary, VLM boundary, prompt renderer, and CSV helpers. Expose one manual/reusable GitHub Actions workflow that validates for free before any paid request.

**Tech Stack:** Python 3.12, httpx, Pillow, OpenRouter Images API, GPT-4.1 Mini JSON evaluation, pytest, Ruff, strict mypy, GitHub Actions.

## Global Constraints

- Hard remaining-allowance floor: `$10.00`.
- Evaluator model, prompt, schema, score scale, and applicability masks are immutable during execution.
- D01-D03 only; H01/H02 are never accessed.
- No automatic retries or hidden resampling.
- Every final candidate is scored and included; the final evaluator cannot select candidates.
- Paid workflow triggers only through `workflow_dispatch` or `workflow_call` with explicit confirmation.
- No API keys, raw inputs, or standalone generated images are committed.

---

### Task 1: Balance boundary and frozen scoring

**Files:**
- Create: `src/weon_eval/budget.py`
- Create: `src/weon_eval/frozen_scoring.py`
- Test: `tests/test_budget.py`
- Test: `tests/test_frozen_scoring.py`

**Interfaces:**
- Produces: `KeyAllowance`, `get_key_allowance(api_key)`, `can_spend(allowance, reserve, floor)`, `score_candidate(...)`, and source applicability constants for D01-D03.

- [ ] Write failing tests for `limit_remaining`, `limit - usage` fallback, missing-limit rejection, floor preservation, raw-response persistence, D03 print/logo N/A, and invalid applicability rejection.
- [ ] Run the narrow tests and verify failure.
- [ ] Implement the minimal HTTP and scoring boundaries with no retries.
- [ ] Run the narrow tests and verify success.
- [ ] Commit with subject `feat: freeze budget and scoring boundaries` and a body explaining the floor and immutable evaluator contract.

### Task 2: Deterministic reference methods

**Files:**
- Create: `src/weon_eval/search_methods.py`
- Modify: `src/weon_eval/runner.py`
- Test: `tests/test_search_methods.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Produces: immutable `SearchMethod` definitions, deterministic garment detail boards, arbitrary prepared-reference payload construction, and fixed two-pass repair prompts.

- [ ] Write failing tests for the exact predeclared method order, detail-board determinism, preserved case/reference ordering, and two-pass final-image behavior.
- [ ] Run the narrow tests and verify failure.
- [ ] Implement the method registry and minimal runner extension without altering existing baseline behavior.
- [ ] Run the narrow tests and verify success.
- [ ] Commit with subject `feat: add predeclared search methods` and a body listing the method families.

### Task 3: Budgeted round-robin orchestrator

**Files:**
- Create: `src/weon_eval/budget_search.py`
- Create: `src/weon_eval/budget_search_cli.py`
- Modify: `pyproject.toml`
- Test: `tests/test_budget_search.py`

**Interfaces:**
- Produces: `run_budget_search(...) -> Path` and `weon-budget-search`.

- [ ] Write failing integration tests with mocked generation, VLM, and balance responses proving D01-D03-only access, round-robin ordering, no evaluator-based selection, failed-method continuation, two-pass accounting, floor stop, request cap, and complete summaries.
- [ ] Run the integration test and verify failure.
- [ ] Implement orchestration and aggregation using the frozen interfaces.
- [ ] Run the integration test and verify success.
- [ ] Commit with subject `feat: orchestrate budgeted method search` and a body explaining ranking and stop conditions.

### Task 4: Guarded paid workflow and documentation

**Files:**
- Create: `.github/workflows/run-budget-search.yml`
- Modify: `README.md`
- Modify: `PLANS.md`
- Test: existing full suite and package build.

**Interfaces:**
- Produces: one manual/reusable paid workflow and documented reproduction/output contract.

- [ ] Add a workflow with explicit confirmation, key guard, dependency sync, Ruff, strict mypy, pytest, build, D01-D03 input preparation, one search command, summary publication, and 14-day artifact upload.
- [ ] Confirm there is no `push`, `pull_request`, or `schedule` paid trigger.
- [ ] Document the frozen-evaluation integrity rules, method list, balance floor, outputs, and limitations.
- [ ] Run `uv sync --dev`, `uv run ruff check .`, `uv run mypy src`, `uv run pytest`, and `uv build`; all must pass.
- [ ] Commit with subject `docs: add guarded budget search workflow` and a detailed body.

### Task 5: Execute and freeze evidence

**Files:**
- Create after execution: `experiments/budget-search.md`
- Create after execution: `experiments/budget-search-method-summary.csv`
- Modify after execution: `REPORT.md`

**Interfaces:**
- Consumes the workflow artifact and produces durable compact evidence only.

- [ ] Execute the workflow once with the repository secret and explicit confirmation.
- [ ] Verify the starting allowance and that every paid call has pre/post balance evidence.
- [ ] Inspect failures for genuine provider errors; do not replace methods or change the evaluator.
- [ ] Verify the stop reason preserves the `$10.00` floor.
- [ ] Download and inspect the artifact, aggregate results, and commit only compact CSV/Markdown evidence and selected contact sheets.
- [ ] Run full CI on the exact evidence head.
- [ ] Commit with subject `docs: record budget search results` and a body containing start/end allowance, spend, requests, winner, and limitations.
