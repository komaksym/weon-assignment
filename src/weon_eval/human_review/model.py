"""Review manifest, validation, aggregation, and export helpers."""

from __future__ import annotations

import copy
import csv
import io
import json
from dataclasses import dataclass
from datetime import date
from statistics import fmean
from typing import Final, TypedDict, cast

ALLOWED_SCORES: Final[frozenset[float]] = frozenset({0.0, 0.5, 1.0})
METHOD_ORDER: Final[tuple[str, ...]] = ("baseline", "structured", "best-of-two")
CASE_ORDER: Final[tuple[str, ...]] = ("D01", "D02", "D03", "H01", "H02")
CASE_TITLES: Final[dict[str, str]] = {
    "D01": "Technical shorts",
    "D02": "Low-top shoes",
    "D03": "Waxed jacket",
    "H01": "Footwear holdout",
    "H02": "Shorts holdout",
}

CASE_FOCUS: Final[dict[str, tuple[str, ...]]] = {
    "D01": (
        "branding and double-button waist",
        "pocket and zipper geometry",
        "reinforcement panels, stitching, hem, and technical fabric",
    ),
    "D02": (
        "ARIGATO branding",
        "toe-panel geometry and sole shape",
        "perforation and leather/suede boundaries",
    ),
    "D03": (
        "collar and front closure",
        "pocket count, seams, and jacket length",
        "dark-green waxed material",
    ),
    "H01": (
        "branding and toe-panel geometry",
        "sole thickness and low-top silhouette",
        "perforation and material boundaries",
    ),
    "H02": (
        "branding and double-button waist",
        "pocket, zipper, and panel geometry",
        "stitching, length, and technical fabric",
    ),
}


@dataclass(frozen=True, slots=True)
class ReviewItem:
    """One generated output to score."""

    item_id: str
    case_id: str
    label: str
    method: str
    split: str

    @property
    def evidence_url(self) -> str:
        return f"/evidence/{self.case_id}.png"


REVIEW_ITEMS: Final[tuple[ReviewItem, ...]] = (
    ReviewItem("D01-A", "D01", "A", "baseline", "development"),
    ReviewItem("D01-B", "D01", "B", "structured", "development"),
    ReviewItem("D01-C", "D01", "C", "best-of-two", "development"),
    ReviewItem("D02-A", "D02", "A", "baseline", "development"),
    ReviewItem("D02-B", "D02", "B", "structured", "development"),
    ReviewItem("D02-C", "D02", "C", "best-of-two", "development"),
    ReviewItem("D03-A", "D03", "A", "baseline", "development"),
    ReviewItem("D03-B", "D03", "B", "structured", "development"),
    ReviewItem("D03-C", "D03", "C", "best-of-two", "development"),
    ReviewItem("H01-H", "H01", "Output", "frozen baseline", "holdout"),
    ReviewItem("H02-H", "H02", "Output", "frozen baseline", "holdout"),
)

ITEM_BY_ID: Final[dict[str, ReviewItem]] = {item.item_id: item for item in REVIEW_ITEMS}


class RaterData(TypedDict):
    name: str
    review_date: str
    review_type: str


class RatingData(TypedDict):
    score: float
    note: str


class ReviewDocument(TypedDict):
    schema_version: int
    rater: RaterData
    ratings: dict[str, RatingData]


def empty_document() -> ReviewDocument:
    """Return a fresh authoritative review document."""

    return {
        "schema_version": 2,
        "rater": {
            "name": "Maksym Koval",
            "review_date": date.today().isoformat(),
            "review_type": "Author human review",
        },
        "ratings": {},
    }


def public_config() -> dict[str, object]:
    """Return browser configuration without revealing development methods."""

    return {
        "score_options": [
            {
                "value": 1.0,
                "label": "Preserved",
                "description": "Garment details remain faithful",
            },
            {
                "value": 0.5,
                "label": "Noticeable drift",
                "description": "Recognizable, but important details changed",
            },
            {
                "value": 0.0,
                "label": "Major failure",
                "description": "Garment identity is not preserved",
            },
        ],
        "items": [
            {
                "item_id": item.item_id,
                "case_id": item.case_id,
                "label": item.label,
                "split": item.split,
                "evidence_url": item.evidence_url,
                "focus": list(CASE_FOCUS[item.case_id]),
            }
            for item in REVIEW_ITEMS
        ],
        "cases": [
            {
                "case_id": case_id,
                "title": CASE_TITLES[case_id],
                "split": "development" if case_id.startswith("D") else "holdout",
                "focus": list(CASE_FOCUS[case_id]),
                "item_ids": [
                    item.item_id for item in REVIEW_ITEMS if item.case_id == case_id
                ],
            }
            for case_id in CASE_ORDER
        ],
    }


def _require_mapping(value: object, *, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    return cast(dict[str, object], value)


def _require_string(value: object, *, path: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{path} must be a string")
    return value


def _validate_score(value: object, *, item_id: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"ratings.{item_id}.score must be numeric")
    score = float(value)
    if score not in ALLOWED_SCORES:
        raise ValueError(f"invalid score for {item_id}: {score}")
    return score


def validate_document(value: object) -> ReviewDocument:
    """Validate and deep-copy a partially completed review document."""

    root = _require_mapping(value, path="document")
    if root.get("schema_version") != 2:
        raise ValueError("schema_version must equal 2")

    rater_raw = _require_mapping(root.get("rater"), path="rater")
    rater: RaterData = {
        "name": _require_string(rater_raw.get("name", ""), path="rater.name"),
        "review_date": _require_string(
            rater_raw.get("review_date", ""), path="rater.review_date"
        ),
        "review_type": _require_string(
            rater_raw.get("review_type", ""), path="rater.review_type"
        ),
    }

    ratings_raw = _require_mapping(root.get("ratings"), path="ratings")
    unknown_items = set(ratings_raw) - set(ITEM_BY_ID)
    if unknown_items:
        raise ValueError(f"ratings contains unknown items: {sorted(unknown_items)}")

    ratings: dict[str, RatingData] = {}
    for item_id, raw_rating in ratings_raw.items():
        rating = _require_mapping(raw_rating, path=f"ratings.{item_id}")
        unknown_fields = set(rating) - {"score", "note"}
        if unknown_fields:
            raise ValueError(
                f"ratings.{item_id} contains unknown fields: {sorted(unknown_fields)}"
            )
        ratings[item_id] = {
            "score": _validate_score(rating.get("score"), item_id=item_id),
            "note": _require_string(rating.get("note", ""), path=f"ratings.{item_id}.note"),
        }

    document: ReviewDocument = {
        "schema_version": 2,
        "rater": rater,
        "ratings": ratings,
    }
    return copy.deepcopy(document)


def _rank_methods(means: dict[str, float | None]) -> list[dict[str, object]]:
    groups: dict[float, list[str]] = {}
    for method in METHOD_ORDER:
        mean = means[method]
        if mean is not None:
            groups.setdefault(mean, []).append(method)
    return [
        {"rank": rank, "methods": methods, "mean": mean}
        for rank, (mean, methods) in enumerate(
            sorted(groups.items(), key=lambda group: group[0], reverse=True),
            start=1,
        )
    ]


def summarize(document: ReviewDocument) -> dict[str, object]:
    """Calculate per-output scores, development means/ranking, and holdouts."""

    outputs: list[dict[str, object]] = []
    method_values: dict[str, list[float]] = {method: [] for method in METHOD_ORDER}
    holdout_scores: dict[str, float] = {}

    for item in REVIEW_ITEMS:
        rating = document["ratings"].get(item.item_id)
        score = rating["score"] if rating is not None else None
        outputs.append(
            {
                "item_id": item.item_id,
                "case_id": item.case_id,
                "label": item.label,
                "method": item.method,
                "split": item.split,
                "score": score,
                "complete": rating is not None,
                "note": rating["note"] if rating is not None else "",
            }
        )
        if score is None:
            continue
        if item.split == "development":
            method_values[item.method].append(score)
        else:
            holdout_scores[item.case_id] = score

    development_means: dict[str, float | None] = {
        method: fmean(values) if values else None for method, values in method_values.items()
    }
    completed = len(document["ratings"])
    return {
        "outputs": outputs,
        "development_method_means": development_means,
        "development_ranking": _rank_methods(development_means),
        "holdout_scores": holdout_scores,
        "completed": completed,
        "total": len(REVIEW_ITEMS),
        "all_complete": completed == len(REVIEW_ITEMS),
    }


def _format_score(score: object) -> str:
    if not isinstance(score, (int, float)):
        return ""
    return f"{float(score):g}"


def _format_mean(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "pending"
    return f"{float(value):.3f}"


def render_csv(document: ReviewDocument) -> str:
    """Render one durable row per generated output."""

    rows = cast(list[dict[str, object]], summarize(document)["outputs"])
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "item_id",
            "case_id",
            "candidate_label",
            "method",
            "split",
            "score",
            "note",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "item_id": row["item_id"],
                "case_id": row["case_id"],
                "candidate_label": row["label"],
                "method": row["method"],
                "split": row["split"],
                "score": _format_score(row["score"]),
                "note": row["note"],
            }
        )
    return output.getvalue()


def render_markdown(document: ReviewDocument) -> str:
    """Render a concise attributed human-review report."""

    summary = summarize(document)
    rater = document["rater"]
    lines = [
        "# Author human-review results",
        "",
        f"- **Rater:** {rater['name'] or 'Not supplied'}",
        f"- **Review date:** {rater['review_date'] or 'Not supplied'}",
        "- **Scale:** 1 = Preserved; 0.5 = Noticeable drift; 0 = Major failure",
        (
            "- **Disclosure:** Attributed author sanity check, "
            "not independent or multi-rater evaluation."
        ),
        "",
        "## Per-output ratings",
        "",
        "| Output | Method | Split | Score | Note |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in cast(list[dict[str, object]], summary["outputs"]):
        label = (
            f"{row['case_id']} — {row['label']}"
            if row["split"] == "development"
            else f"{row['case_id']} — output"
        )
        note = cast(str, row["note"]).replace("|", "\\|") or "—"
        lines.append(
            f"| {label} | {row['method']} | {row['split']} | "
            f"{_format_score(row['score']) or '—'} | {note} |"
        )

    lines.extend(["", "## Development method means", ""])
    means = cast(dict[str, object], summary["development_method_means"])
    for method in METHOD_ORDER:
        lines.append(f"- **{method}:** {_format_mean(means[method])}")

    lines.extend(["", "## Development ranking", ""])
    ranking = cast(list[dict[str, object]], summary["development_ranking"])
    if ranking:
        for group in ranking:
            methods = " = ".join(cast(list[str], group["methods"]))
            lines.append(f"- **Rank {group['rank']}:** {methods} ({_format_mean(group['mean'])})")
    else:
        lines.append("- Pending")

    lines.extend(["", "## Frozen holdouts", ""])
    holdouts = cast(dict[str, float], summary["holdout_scores"])
    for case_id in ("H01", "H02"):
        lines.append(f"- **{case_id}:** {_format_score(holdouts.get(case_id)) or 'pending'}")

    lines.extend(["", f"Completed outputs: **{summary['completed']}/{summary['total']}**."])
    return "\n".join(lines) + "\n"


def render_json(document: ReviewDocument) -> str:
    """Render validated ratings plus calculated summaries."""

    return json.dumps(
        {"review": document, "summary": summarize(document)},
        indent=2,
        sort_keys=True,
    ) + "\n"
