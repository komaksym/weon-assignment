"""Load the small experiment case matrix."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CaseError(ValueError):
    """Raised when the case file is malformed."""


@dataclass(frozen=True)
class Case:
    """One model, environment, and one or more garment references."""

    id: str
    split: str
    model: Path
    environment: Path
    garments: tuple[Path, ...]

    @property
    def reference_paths(self) -> tuple[Path, ...]:
        """Return references in the order expected by the image model."""

        return (self.model, self.environment, *self.garments)


def _required_string(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise CaseError(f"{key} must be a non-empty string")
    return value


def load_cases(path: Path) -> dict[str, Case]:
    """Load cases keyed by their unique IDs."""

    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CaseError(f"cannot load cases: {exc}") from exc

    raw_cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(raw_cases, list):
        raise CaseError("cases must be a list")

    cases: dict[str, Case] = {}
    for raw in raw_cases:
        if not isinstance(raw, dict):
            raise CaseError("each case must be an object")

        case_id = _required_string(raw, "id")
        if case_id in cases:
            raise CaseError(f"duplicate case id: {case_id}")

        raw_garments = raw.get("garments")
        if not isinstance(raw_garments, list) or not raw_garments:
            raise CaseError(f"{case_id}: garments must be a non-empty list")
        if not all(isinstance(item, str) and item for item in raw_garments):
            raise CaseError(f"{case_id}: garment paths must be non-empty strings")

        cases[case_id] = Case(
            id=case_id,
            split=_required_string(raw, "split"),
            model=Path(_required_string(raw, "model")),
            environment=Path(_required_string(raw, "environment")),
            garments=tuple(Path(item) for item in raw_garments),
        )

    return cases
