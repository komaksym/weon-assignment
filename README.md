# WEON Garment Consistency Evaluation

A small experiment for testing practical ways to preserve garment details in black-box AI photoshoots.

The repository intentionally prioritizes generated evidence and evaluation over production infrastructure. It uses three development cases to compare a direct baseline, structured prompting, and best-of-two selection. Two additional cases are held out until the strategy and scoring rubric are fixed.

## System

```mermaid
flowchart LR
    A[cases.json + asset sources] --> B[Prepare selected inputs]
    B --> C[Prompt]
    C --> D[OpenRouter Images API]
    D --> E[image.png + metadata.json]
    E --> F[Evaluation and report]
```

## Setup

Requirements: Python 3.12+ and `uv`.

```bash
uv sync --dev
cp .env.example .env
```

The ignored local input layout is:

```text
inputs/
├── environments/
│   ├── street.png
│   ├── meadow.png
│   └── forest.png
├── garments/
│   ├── shorts.png
│   ├── sneakers.jpg
│   └── coat.png
└── models/
    ├── black-bodysuit-woman.png
    ├── white-tee-man.png
    └── cream-sweater-woman.png
```

The filename extensions follow the actual downloaded bytes rather than the source URL suffixes.

Prepare only the selected development case from the assignment-provided source manifest:

```bash
uv run weon-prepare-inputs D01
```

Set `OPENROUTER_API_KEY` in your shell or load it from `.env` before running the generation command. The CLI does not read or print the key.

## Run one baseline locally

```bash
export OPENROUTER_API_KEY="..."
uv run weon-eval D01
```

## Run one paid experiment in GitHub Actions

The permanent **Run paid experiment** workflow is manual and separate from normal CI:

1. Open **Actions → Run paid experiment → Run workflow**.
2. Choose `D01`, `D02`, or `D03`.
3. Enter the OpenRouter model slug.
4. Enable **Confirm that this workflow may spend API credit**.
5. Start the workflow and download the `experiment-<case>-<run-id>` artifact.

Each invocation validates the repository, prepares only the selected case, performs one generation command without retries, and uploads the case output for 14 days. Ordinary pushes and pull requests never trigger this paid workflow.

Holdout cases are blocked during development. The explicit local override is reserved for the frozen final evaluation:

```bash
uv run weon-eval H01 --allow-holdout
```

The result is written to:

```text
outputs/<case>/<model>/<strategy>/
├── image.png
└── metadata.json
```

Metadata records the prompt, references, model, baseline strategy, API-reported cost, and measured request latency. Existing output directories are not overwritten. Inspect an existing result before deciding whether another paid request is justified.

## Validation

```bash
uv run pytest
uv run ruff check .
uv run mypy src
uv build
```

No automated test sends a real API request.
