# Human Review App Design

## Goal

Replace the copy-and-fill Markdown review form with a tiny local web application that lets the assignment author score all frozen garment outputs with minimal interaction.

## Scope

The application starts with `uv run weon-human-review`, opens in the browser, and uses only the Python standard library plus the repository's existing assets. It does not add a database, frontend framework, authentication, network service, or production dependency.

## Workflow

1. Show one review target at a time in the fixed order D01 A/B/C, D02 A/B/C, D03 A/B/C, H01, H02.
2. Display the existing high-resolution case review sheet and a prominent current-candidate label.
3. Offer one-click presets: preserved (`1`), partial drift (`0.5`), and major drift (`0`). A preset fills all six frozen dimensions and advances to the next item.
4. Allow individual score corrections with `1`, `0.5`, `0`, and `N/A (-1)` controls.
5. Allow optional issue tags and one short note.
6. Auto-save every change to `submission/human-review-ratings.json`.
7. Show progress and permit previous/next navigation without losing state.
8. Provide a final summary and JSON, CSV, and Markdown exports.

## Evaluation contract

The app preserves the existing dimensions and score values exactly:

- color;
- print/logo;
- silhouette/length;
- construction details;
- texture/material;
- garment presence;
- scores `1`, `0.5`, `0`, or `-1` for genuinely inapplicable source dimensions.

Development candidates are presented as A/B/C in the app. Their method mapping is retained only on the server and included in exports; the underlying committed review sheets are served unchanged. Holdouts remain reported separately from development method means.

## Architecture

- `model.py`: immutable review manifest, validation, aggregation, and export rendering.
- `server.py`: local `ThreadingHTTPServer`, static asset serving, evidence serving, and atomic JSON persistence.
- `static/`: one HTML page, one CSS file, and one JavaScript controller with no build step.
- `human_review_cli.py`: command-line arguments, repository-root discovery, browser launch, and server lifecycle.

## Persistence and errors

Each save validates score values and item IDs before replacing the JSON file atomically. Invalid requests return a JSON `400` response and do not modify the last valid file. Missing evidence returns `404` with the exact expected repository path. The app can resume from a partially completed file.

## Verification

- Unit tests cover score validation, N/A-aware means, blind public configuration, method aggregation, exports, and persisted-state round trips.
- HTTP integration tests cover config, save, resume, evidence, and export routes.
- Browser QA covers preset-and-next, per-dimension correction, reload persistence, summary, export, desktop layout, and mobile layout.
- Repository validation remains Ruff, strict mypy, pytest, and package build.
