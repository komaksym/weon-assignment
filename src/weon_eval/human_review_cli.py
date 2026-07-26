"""Command-line entry point for the local human-review app."""

from __future__ import annotations

import argparse
import threading
import webbrowser
from pathlib import Path

from weon_eval.human_review.server import create_server


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Run the local WEON human-review app")
    result.add_argument("--host", default="127.0.0.1")
    result.add_argument("--port", type=int, default=8765)
    result.add_argument(
        "--data",
        type=Path,
        default=Path("submission/human-review-ratings.json"),
        help="ratings JSON path, relative to the repository root by default",
    )
    result.add_argument("--no-browser", action="store_true")
    return result


def find_repo_root(start: Path) -> Path:
    """Find a repository containing pyproject.toml and submission/review."""

    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "submission" / "review"
        ).is_dir():
            return candidate
    raise FileNotFoundError(
        "could not find repository root containing pyproject.toml and submission/review"
    )


def main() -> int:
    args = parser().parse_args()
    if not 0 <= args.port <= 65535:
        print("port must be between 0 and 65535")
        return 2
    try:
        repo_root = find_repo_root(Path.cwd())
        server = create_server(
            host=args.host,
            port=args.port,
            repo_root=repo_root,
            data_path=args.data,
        )
    except (OSError, ValueError) as exc:
        print(str(exc))
        return 1

    url = f"http://{args.host}:{server.server_port}/"
    print(f"Human review app: {url}")
    print("Press Ctrl+C to stop. Progress auto-saves after every edit.")
    if not args.no_browser:
        threading.Timer(0.25, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping human review app.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
