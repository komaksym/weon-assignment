import json
import sys
from pathlib import Path

from weon_eval import __main__ as cli


def _write_case(path: Path, split: str) -> None:
    path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "H01",
                        "split": split,
                        "model": "model.png",
                        "environment": "environment.png",
                        "garments": ["garment.png"],
                    }
                ]
            }
        )
    )


def test_cli_rejects_holdout_without_explicit_flag(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    cases = tmp_path / "cases.json"
    _write_case(cases, "holdout")
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret")
    monkeypatch.setattr(
        sys,
        "argv",
        ["weon-eval", "H01", "--cases", str(cases)],
    )
    monkeypatch.setattr(
        cli,
        "run_case",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("holdout reached generation")),
    )

    assert cli.main() == 2
    assert "requires --allow-holdout" in capsys.readouterr().out


def test_cli_has_no_free_form_strategy_option() -> None:
    actions = {action.dest for action in cli._parser()._actions}

    assert "strategy" not in actions


def test_cli_allows_explicit_holdout_and_records_baseline_strategy(
    tmp_path: Path, monkeypatch
) -> None:
    cases = tmp_path / "cases.json"
    prompt = tmp_path / "baseline.txt"
    _write_case(cases, "holdout")
    prompt.write_text("{garment_roles}\n")
    captured: dict[str, object] = {}

    def fake_run_case(**kwargs: object) -> Path:
        captured.update(kwargs)
        return tmp_path / "outputs"

    monkeypatch.setenv("OPENROUTER_API_KEY", "secret")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "weon-eval",
            "H01",
            "--cases",
            str(cases),
            "--prompt",
            str(prompt),
            "--allow-holdout",
        ],
    )
    monkeypatch.setattr(cli, "run_case", fake_run_case)

    assert cli.main() == 0
    assert captured["strategy"] == "baseline"
