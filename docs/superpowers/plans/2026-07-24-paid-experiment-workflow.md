# Paid Experiment Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a permanent manual GitHub Actions workflow that prepares assignment inputs, runs exactly one requested development experiment, and uploads the generated image and metadata without coupling paid calls to normal CI.

**Architecture:** A tested Python input-preparation command reads `cases.json` and `asset_sources.json`, downloads only the selected case references, and validates that their bytes match their filename extensions. A reusable GitHub Actions workflow performs free validation before one paid CLI call and uploads outputs as an artifact. Slice 2 is triggered once through a temporary PR-event caller, inspected, recorded, and then the caller is deleted.

**Tech Stack:** Python 3.12, httpx, pytest, Ruff, mypy, uv, GitHub Actions.

## Global Constraints

- The permanent paid workflow is triggered by `workflow_dispatch` or `workflow_call`, never by `push`, `pull_request`, or `schedule` directly.
- Normal CI remains free and unchanged.
- The workflow accepts only development cases `D01`, `D02`, and `D03` in this slice.
- Each workflow invocation runs exactly one case, one model, one prompt, one candidate, and no retry.
- `OPENROUTER_API_KEY` is consumed only from GitHub Actions secrets and is never printed or persisted.
- Generated inputs and outputs remain Git-ignored and are shared only as short-lived workflow artifacts.
- No holdout case is prepared or executed.
- No new production dependency is added.

---

### Task 1: Tested assignment input preparation

**Files:**
- Create: `asset_sources.json`
- Create: `src/weon_eval/assets.py`
- Create: `src/weon_eval/prepare_inputs.py`
- Create: `tests/test_assets.py`
- Modify: `pyproject.toml`
- Modify: `cases.json`
- Modify: `README.md`

**Interfaces:**
- Consumes: `load_cases(path: Path) -> dict[str, Case]` and `Case.reference_paths`.
- Produces: `prepare_case_inputs(case: Case, sources_path: Path, downloader: Downloader = download_asset) -> tuple[Path, ...]` and CLI command `weon-prepare-inputs CASE_ID`.

- [ ] **Step 1: Add failing tests**

Test that preparation downloads only the selected case references in order, creates parent directories, writes image bytes, rejects missing source mappings, and rejects image bytes whose format does not match the target suffix.

- [ ] **Step 2: Verify the focused tests fail**

Run: `uv run pytest tests/test_assets.py -v`

Expected: collection failure because `weon_eval.assets` does not exist.

- [ ] **Step 3: Implement the minimal downloader and CLI**

Use `httpx.get(..., follow_redirects=True, timeout=120)`. Accept PNG magic bytes for `.png` and JPEG magic bytes for `.jpg`/`.jpeg`. Download only `case.reference_paths`; do not add caching, retries, checksums, or a general asset manager.

- [ ] **Step 4: Correct source file extensions**

Set each local garment path to match the downloaded bytes rather than the source URL suffix: shorts and coat are PNG, while sneakers are JPEG. This prevents incorrect `Content-Type` data URLs while preserving strict format validation.

- [ ] **Step 5: Verify the task**

Run:

```bash
uv run pytest tests/test_assets.py -v
uv run pytest
uv run ruff check .
uv run mypy src
uv build
```

Expected: all commands pass.

- [ ] **Step 6: Commit**

```text
feat: prepare experiment inputs

Add a small tested command that downloads only the selected case references
from the assignment source manifest and validates their image formats. Correct
garment filename extensions so generated data URLs use the real media type.
```

### Task 2: Permanent guarded paid workflow

**Files:**
- Create: `.github/workflows/run-experiment.yml`
- Modify: `README.md`
- Modify: `spec.md`

**Interfaces:**
- Consumes: `weon-prepare-inputs`, `weon-eval`, `secrets.OPENROUTER_API_KEY`.
- Produces: artifact `experiment-<case>-<run-id>` containing `outputs/<case>/<model>/baseline/image.png` and `metadata.json`.

- [ ] **Step 1: Add the reusable manual workflow**

Define `workflow_dispatch` inputs for `case_id`, `model`, and a required `confirm_paid_run` boolean. Define matching `workflow_call` inputs. Restrict `case_id` to D01-D03 in the dispatch UI and reject any other value in a shell guard.

- [ ] **Step 2: Add spending and concurrency guards**

Require `confirm_paid_run == true`, fail when the API secret is absent, use a `paid-experiment-<case>` concurrency group with `cancel-in-progress: false`, set a 15-minute timeout, and perform no retry.

- [ ] **Step 3: Add execution and artifact publication**

Run dependency sync, Ruff, mypy, pytest, and build before preparing inputs. Then call `weon-prepare-inputs` and `weon-eval` once. Upload the selected case output directory with 14-day retention.

- [ ] **Step 4: Document the manual path**

Explain the Actions UI steps, one-call semantics, artifact location, and why the workflow is separate from CI. Update `spec.md` so the approved automation path is part of slice 2.

- [ ] **Step 5: Verify free CI**

Run the repository CI on the final workflow commit. Expected: dependency sync, Ruff, strict mypy, tests, and build all pass; no paid workflow starts from the push or PR update.

- [ ] **Step 6: Commit**

```text
ci: add manual paid experiment workflow

Add a permanent workflow-dispatch entry point for one guarded experiment run.
Keep it separate from normal CI, validate before spending, prepare only the
selected development case, and publish generated outputs as an artifact.
```

### Task 3: Execute and record D01 once

**Files:**
- Temporarily create: `.github/workflows/run-d01-once.yml`
- Modify: `experiments/D01-baseline.md`
- Delete: `.github/workflows/run-d01-once.yml`

**Interfaces:**
- Consumes: reusable workflow `.github/workflows/run-experiment.yml` and repository secret `OPENROUTER_API_KEY`.
- Produces: one D01 workflow artifact and a completed experiment record.

- [ ] **Step 1: Add the one-time caller**

Trigger only on PR `ready_for_review`, guard to PR #2 and the same-repository branch, call the permanent workflow with D01, Seedream 4.5, and `confirm_paid_run: true`, and inherit secrets.

- [ ] **Step 2: Trigger exactly once**

Convert PR #2 to draft, then mark it ready for review. Confirm only one paid workflow job starts.

- [ ] **Step 3: Inspect the workflow result**

Confirm the workflow made one request, download its artifact, open `image.png`, and inspect `metadata.json` for case identity, model, baseline strategy, ordered references, cost, and latency.

- [ ] **Step 4: Record manual evidence**

Replace the blocked record with the execution timestamp, command, request count, cost, latency, composition mechanics, garment-dimension labels, anomalies, and explicit `proceed to slice 3` or `blocked` decision.

- [ ] **Step 5: Remove the one-time caller**

Delete `.github/workflows/run-d01-once.yml`. Verify `.github/workflows/run-experiment.yml` remains manual/reusable and normal CI remains green.

- [ ] **Step 6: Commit**

```text
docs: record first D01 baseline

Record the single paid Seedream baseline, measured cost and latency, manual
reference comparison, and slice-3 decision. Remove the temporary trigger while
retaining the permanent manual experiment workflow.
```

## Final Verification

- [ ] `uv run ruff check .`
- [ ] `uv run mypy src`
- [ ] `uv run pytest`
- [ ] `uv build`
- [ ] Permanent paid workflow has no automatic event trigger.
- [ ] Exactly one D01 live request was made.
- [ ] No D02, D03, H01, or H02 request was made.
- [ ] Generated files are artifacts, not repository files.
- [ ] PR includes the system DAG, per-file summary, request count, cost, latency, inspection result, and AI disclosure where applicable.
