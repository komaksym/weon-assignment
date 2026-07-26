"""Dependency-free local HTTP server for the human-review app."""

from __future__ import annotations

import json
import mimetypes
import os
import shutil
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Final
from urllib.parse import unquote, urlparse

from weon_eval.human_review.model import (
    ReviewDocument,
    empty_document,
    public_config,
    render_csv,
    render_json,
    render_markdown,
    summarize,
    validate_document,
)

STATIC_ROOT: Final[Path] = Path(__file__).with_name("static")
MAX_REQUEST_BYTES: Final[int] = 1_000_000


class ReviewStore:
    """Atomically persist one review document."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> ReviewDocument:
        if not self.path.exists():
            return empty_document()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"could not read review data at {self.path}: {exc}") from exc
        if isinstance(value, dict) and value.get("schema_version") == 1:
            archive = self.path.with_name(f"{self.path.stem}.legacy-v1{self.path.suffix}")
            shutil.copy2(self.path, archive)
            document = empty_document()
            self.save(document)
            return document
        return validate_document(value)

    def save(self, document: ReviewDocument) -> None:
        validated = validate_document(document)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(validated, indent=2, sort_keys=True) + "\n"
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(payload)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()


def _safe_case_id(raw: str) -> str | None:
    if len(raw) != 3 or raw[0] not in {"D", "H"} or not raw[1:].isdigit():
        return None
    return raw


def make_handler(*, repo_root: Path, store: ReviewStore) -> type[BaseHTTPRequestHandler]:
    """Create a request handler bound to repository and storage paths."""

    class ReviewHandler(BaseHTTPRequestHandler):
        server_version = "WEONHumanReview/1.0"

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_bytes(
            self,
            body: bytes,
            *,
            content_type: str,
            status: HTTPStatus = HTTPStatus.OK,
            filename: str | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if filename is not None:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def _send_json(
            self,
            value: object,
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self._send_bytes(
                json.dumps(value, sort_keys=True).encode("utf-8"),
                content_type="application/json; charset=utf-8",
                status=status,
            )

        def _send_error_json(self, message: str, status: HTTPStatus) -> None:
            self._send_json({"error": message}, status=status)

        def _serve_static(self, relative_path: str) -> None:
            file_path = (STATIC_ROOT / relative_path).resolve()
            try:
                file_path.relative_to(STATIC_ROOT.resolve())
            except ValueError:
                self._send_error_json("invalid static path", HTTPStatus.BAD_REQUEST)
                return
            if not file_path.is_file():
                self._send_error_json("static file not found", HTTPStatus.NOT_FOUND)
                return
            content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            self._send_bytes(file_path.read_bytes(), content_type=content_type)

        def _serve_evidence(self, path: str) -> None:
            raw_name = unquote(path.removeprefix("/evidence/"))
            if "/" in raw_name or "\\" in raw_name or not raw_name.endswith(".png"):
                self._send_error_json("invalid evidence path", HTTPStatus.BAD_REQUEST)
                return
            case_id = _safe_case_id(raw_name.removesuffix(".png"))
            if case_id is None:
                self._send_error_json("invalid case id", HTTPStatus.BAD_REQUEST)
                return
            evidence_path = repo_root / "submission" / "review" / f"{case_id}-human-review.png"
            if not evidence_path.is_file():
                self._send_error_json(
                    f"evidence not found: {evidence_path}",
                    HTTPStatus.NOT_FOUND,
                )
                return
            self._send_bytes(evidence_path.read_bytes(), content_type="image/png")

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            try:
                if path == "/":
                    self._serve_static("index.html")
                elif path == "/static/app.js":
                    self._serve_static("app.js")
                elif path == "/static/styles.css":
                    self._serve_static("styles.css")
                elif path == "/api/config":
                    self._send_json(public_config())
                elif path == "/api/review":
                    self._send_json(store.load())
                elif path == "/api/summary":
                    self._send_json(summarize(store.load()))
                elif path == "/api/export/ratings.json":
                    self._send_bytes(
                        render_json(store.load()).encode("utf-8"),
                        content_type="application/json; charset=utf-8",
                        filename="human-review-ratings.json",
                    )
                elif path == "/api/export/ratings.csv":
                    self._send_bytes(
                        render_csv(store.load()).encode("utf-8"),
                        content_type="text/csv; charset=utf-8",
                        filename="human-review-ratings.csv",
                    )
                elif path == "/api/export/report.md":
                    self._send_bytes(
                        render_markdown(store.load()).encode("utf-8"),
                        content_type="text/markdown; charset=utf-8",
                        filename="human-review-results.md",
                    )
                elif path.startswith("/evidence/"):
                    self._serve_evidence(path)
                else:
                    self._send_error_json("not found", HTTPStatus.NOT_FOUND)
            except (OSError, ValueError) as exc:
                self._send_error_json(str(exc), HTTPStatus.INTERNAL_SERVER_ERROR)

        def do_PUT(self) -> None:
            path = urlparse(self.path).path
            if path != "/api/review":
                self._send_error_json("not found", HTTPStatus.NOT_FOUND)
                return
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_error_json("invalid content length", HTTPStatus.BAD_REQUEST)
                return
            if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
                self._send_error_json("invalid request size", HTTPStatus.BAD_REQUEST)
                return
            try:
                raw = self.rfile.read(content_length)
                value = json.loads(raw)
                document = validate_document(value)
                store.save(document)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"saved": True})

    return ReviewHandler


def create_server(
    *,
    host: str,
    port: int,
    repo_root: Path,
    data_path: Path,
) -> ThreadingHTTPServer:
    """Create, but do not start, the local review server."""

    resolved_root = repo_root.resolve()
    resolved_data = data_path if data_path.is_absolute() else resolved_root / data_path
    handler = make_handler(repo_root=resolved_root, store=ReviewStore(resolved_data))
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
