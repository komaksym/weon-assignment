from __future__ import annotations

import csv
import io
import json
import threading
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from weon_eval.human_review.model import (
    DIMENSIONS,
    empty_document,
    public_config,
    render_csv,
    render_markdown,
    summarize,
    validate_document,
)
from weon_eval.human_review.server import ReviewStore, create_server
from weon_eval.human_review_cli import find_repo_root, parser


def _scores(value: float = 1.0) -> dict[str, float]:
    return {dimension: value for dimension in DIMENSIONS}


def _complete_document() -> dict[str, Any]:
    document = empty_document()
    ratings = document["ratings"]
    assert isinstance(ratings, dict)
    for item_id in (
        "D01-A",
        "D01-B",
        "D01-C",
        "D02-A",
        "D02-B",
        "D02-C",
        "D03-A",
        "D03-B",
        "D03-C",
        "H01-H",
        "H02-H",
    ):
        ratings[item_id] = {
            "scores": _scores(),
            "issues": [],
            "note": "",
        }
    return document


def _request(url: str, *, method: str = "GET", payload: object | None = None) -> tuple[int, bytes]:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def test_summary_excludes_na_and_missing_scores() -> None:
    document = _complete_document()
    ratings = document["ratings"]
    assert isinstance(ratings, dict)
    ratings["D01-A"] = {
        "scores": {
            "color": 1.0,
            "print_logo": -1.0,
            "silhouette_length": 0.5,
            "construction_details": 0.0,
        },
        "issues": ["construction"],
        "note": "zipper moved",
    }

    summary = summarize(validate_document(document))

    outputs = summary["outputs"]
    assert isinstance(outputs, list)
    d01_a = next(row for row in outputs if row["item_id"] == "D01-A")
    assert d01_a["mean"] == pytest.approx(0.5)
    assert d01_a["complete"] is False


def test_validate_document_rejects_unknown_score_without_mutating_input() -> None:
    document = _complete_document()
    ratings = document["ratings"]
    assert isinstance(ratings, dict)
    ratings["D01-A"]["scores"]["color"] = 0.75

    with pytest.raises(ValueError, match="invalid score"):
        validate_document(document)

    assert ratings["D01-A"]["scores"]["color"] == 0.75


def test_public_config_hides_method_names() -> None:
    config = public_config()
    serialized = json.dumps(config)

    assert "baseline" not in serialized
    assert "structured" not in serialized
    assert "best-of-two" not in serialized
    assert [item["label"] for item in config["items"][:3]] == ["A", "B", "C"]


def test_summary_computes_development_method_means_and_separate_holdouts() -> None:
    document = _complete_document()
    ratings = document["ratings"]
    assert isinstance(ratings, dict)
    ratings["D01-A"]["scores"] = _scores(0.0)
    ratings["D02-A"]["scores"] = _scores(0.5)
    ratings["D03-A"]["scores"] = _scores(1.0)
    ratings["H01-H"]["scores"] = _scores(0.5)
    ratings["H02-H"]["scores"] = _scores(1.0)

    summary = summarize(validate_document(document))

    assert summary["development_method_means"]["baseline"] == pytest.approx(0.5)
    assert summary["development_method_means"]["structured"] == pytest.approx(1.0)
    assert summary["development_method_means"]["best-of-two"] == pytest.approx(1.0)
    assert summary["holdout_means"] == {"H01": 0.5, "H02": 1.0}


def test_exports_include_raw_ratings_means_and_method_mapping() -> None:
    document = validate_document(_complete_document())

    markdown = render_markdown(document)
    rows = list(csv.DictReader(io.StringIO(render_csv(document))))

    assert "D01 — baseline" in markdown
    assert "Development method means" in markdown
    assert rows[0]["item_id"] == "D01-A"
    assert rows[0]["method"] == "baseline"
    assert rows[0]["mean"] == "1.0000"


def test_review_store_returns_empty_document_and_round_trips_atomically(tmp_path: Path) -> None:
    path = tmp_path / "submission" / "human-review-ratings.json"
    store = ReviewStore(path)

    assert store.load() == empty_document()

    document = validate_document(_complete_document())
    store.save(document)

    assert store.load() == document
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1
    assert not list(path.parent.glob("*.tmp"))


def test_http_api_saves_resumes_serves_evidence_and_exports(tmp_path: Path) -> None:
    repo_root = tmp_path
    evidence_dir = repo_root / "submission" / "review"
    evidence_dir.mkdir(parents=True)
    evidence = b"\x89PNG\r\n\x1a\nfixture"
    (evidence_dir / "D01-human-review.png").write_bytes(evidence)
    data_path = repo_root / "submission" / "human-review-ratings.json"
    server = create_server(
        host="127.0.0.1",
        port=0,
        repo_root=repo_root,
        data_path=data_path,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        status, body = _request(f"{base_url}/")
        assert status == 200
        assert b"Human garment review" in body
        assert b"preserved-next" in body

        status, body = _request(f"{base_url}/static/app.js")
        assert status == 200
        assert b"saveAndAdvance" in body

        status, body = _request(f"{base_url}/api/config")
        assert status == 200
        assert len(json.loads(body)["items"]) == 11

        status, body = _request(f"{base_url}/api/review")
        assert status == 200
        assert json.loads(body) == empty_document()

        document = _complete_document()
        status, body = _request(f"{base_url}/api/review", method="PUT", payload=document)
        assert status == 200
        assert json.loads(body)["saved"] is True

        status, body = _request(f"{base_url}/api/review")
        assert status == 200
        assert json.loads(body)["ratings"]["D01-A"]["scores"]["color"] == 1.0

        status, body = _request(f"{base_url}/evidence/D01.png")
        assert status == 200
        assert body == evidence

        status, body = _request(f"{base_url}/api/export/report.md")
        assert status == 200
        assert b"Development method means" in body

        status, body = _request(f"{base_url}/evidence/../../pyproject.toml")
        assert status in {400, 404}
        assert b"project" not in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_api_rejects_invalid_save_and_keeps_previous_state(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "submission" / "review").mkdir(parents=True)
    data_path = repo_root / "submission" / "human-review-ratings.json"
    store = ReviewStore(data_path)
    valid = validate_document(_complete_document())
    store.save(valid)
    server = create_server(
        host="127.0.0.1",
        port=0,
        repo_root=repo_root,
        data_path=data_path,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        invalid = _complete_document()
        invalid["ratings"]["D01-A"]["scores"]["color"] = 0.75
        status, body = _request(f"{base_url}/api/review", method="PUT", payload=invalid)
        assert status == 400
        assert b"invalid score" in body
        assert store.load() == valid
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_cli_parser_and_repo_root_discovery(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    nested = root / "src" / "weon_eval"
    nested.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (root / "submission" / "review").mkdir(parents=True)

    assert find_repo_root(nested) == root

    args = parser().parse_args(["--port", "9000", "--no-browser"])
    assert args.host == "127.0.0.1"
    assert args.port == 9000
    assert args.no_browser is True
