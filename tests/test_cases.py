from pathlib import Path

import pytest

from weon_eval.cases import CaseError, load_cases


def test_load_cases_preserves_reference_order(tmp_path: Path) -> None:
    path = tmp_path / "cases.json"
    path.write_text(
        '''{
          "cases": [
            {
              "id": "D01",
              "split": "development",
              "model": "inputs/models/person.png",
              "environment": "inputs/environments/street.png",
              "garments": ["inputs/garments/shorts.png"]
            }
          ]
        }'''
    )

    case = load_cases(path)["D01"]

    assert case.reference_paths == (
        Path("inputs/models/person.png"),
        Path("inputs/environments/street.png"),
        Path("inputs/garments/shorts.png"),
    )


def test_load_cases_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "cases.json"
    path.write_text(
        '''{
          "cases": [
            {
              "id": "D01",
              "split": "development",
              "model": "m.png",
              "environment": "e.png",
              "garments": ["g.png"]
            },
            {
              "id": "D01",
              "split": "holdout",
              "model": "m2.png",
              "environment": "e2.png",
              "garments": ["g2.png"]
            }
          ]
        }'''
    )

    with pytest.raises(CaseError, match="duplicate case id: D01"):
        load_cases(path)
