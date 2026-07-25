"""Frozen rubric, validation, aggregation, and export helpers for human review."""

from __future__ import annotations

import copy
import csv
import io
import json
from dataclasses import dataclass
from datetime import date
from statistics import fmean
from typing import Final, TypedDict, cast

DIMENSIONS: Final[tuple[str, ...]] = (
    "color",
    "print_logo",
    "silhouette_length",
    "construction_details",
    "texture_material",
    "garment_presence",
)

DIMENSION_LABELS: Final[dict[str, str]] = {
    "color": "Color",
    "print_logo": "Print/logo",
    "silhouette_length": "Silhouette/length",
    "construction_details": "Construction details",
    "texture_material": "Texture/material",
    "garment_presence": "Garment presence",
}

ALLOWED_SCORES: Final[frozenset[float]] = frozenset({-1.0, 0.0, 0.5, 1.0})
ISSUE_TAGS: Final[tuple[str, ...]] = (
    "color",
    "logo/text",
    "silhouette",
    "construction",
    "material",
    "presence",
    "lighting confound",
    "pose confound",
)

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
    """One candidate to score."""

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
    ReviewItem("H01-H", "H01", "Frozen output", "frozen baseline", "holdout"),
    ReviewItem("H02-H", "H02", "Frozen output", "frozen baseline", "holdout"),
)

ITEM_BY_ID: Final[dict[str, ReviewItem]] = {item.item_id: item for item in REVIEW_ITEMS}


class RaterData(TypedDict):
    name: str
    review_date: str
    review_type: str


class RatingData(TypedDict):
    scores: dict[str, float]
    issues: list[str]
    note: str


class OverallData(TypedDict):
    structured_outperformed: str
    structured_reason: str
    best_of_two_outperformed: str
    best_of_two_reason: str
    brand_critical_ready: str
    brand_critical_reason: str
    automatic_perfect_errors: str
    automatic_perfect_examples: str
    preferred_method: str
    preferred_method_reason: str


class ReviewDocument(TypedDict):
    schema_version: int
    rater: RaterData
    ratings: dict[str, RatingData]
    overall: OverallData


def empty_document() -> ReviewDocument:
    """Return a fresh, partially completable review document."""

    return {
        "schema_version": 1,
        "rater": {
            "name": "Maksym Koval",
            "review_date": date.today().isoformat(),
            "review_type": "Author human review",
        },
        "ratings": {},
        "overall": {
            "structured_outperformed": "",
            "structured_reason": "",
            "best_of_two_outperformed": "",
            "best_of_two_reason": "",
            "brand_critical_ready": "",
            "brand_critical_reason": "",
            "automatic_perfect_errors": "",
            "automatic_perfect_examples": "",
            "preferred_method": "",
            "preferred_method_reason": "",
        },
    }


def public_config() -> dict[str, object]:
    """Return UI configuration without method identities."""

    return {
        "dimensions": [
            {"id": dimension, "label": DIMENSION_LABELS[dimension]} for dimension in DIMENSIONS
        ],
        "score_options": [
            {"value": 1.0, "label": "1", "description": "Preserved"},
            {"value": 0.5, "label": "0.5", "description": "Partially preserved"},
            {"value": 0.0, "label": "0", "description": "Drifted"},
            {"value": -1.0, "label": "N/A", "description": "Not applicable in source"},
        ],
        "issue_tags": list(ISSUE_TAGS),
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
    }


def _require_mapping(value: object, *, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    return cast(dict[str, object], value)


def _require_string(value: object, *, path: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{path} must be a string")
    return value


def _validate_scores(value: object, *, item_id: str) -> dict[str, float]:
    raw_scores = _require_mapping(value, path=f"ratings.{item_id}.scores")
    unknown = set(raw_scores) - set(DIMENSIONS)
    if unknown:
        raise ValueError(f"ratings.{item_id}.scores contains unknown dimensions: {sorted(unknown)}")
    scores: dict[str, float] = {}
    for dimension, raw_score in raw_scores.items():
        if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
            raise ValueError(f"ratings.{item_id}.{dimension} must be numeric")
        score = float(raw_score)
        if score not in ALLOWED_SCORES:
            raise ValueError(f"invalid score for {item_id}.{dimension}: {score}")
        scores[dimension] = score
    return scores


def validate_document(value: object) -> ReviewDocument:
    """Validate and deep-copy a partially completed review document."""

    root = _require_mapping(value, path="document")
    if root.get("schema_version") != 1:
        raise ValueError("schema_version must equal 1")

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
        rating_map = _require_mapping(raw_rating, path=f"ratings.{item_id}")
        raw_issues = rating_map.get("issues", [])
        issues_are_strings = isinstance(raw_issues, list) and all(
            isinstance(issue, str) for issue in raw_issues
        )
        if not issues_are_strings:
            raise ValueError(f"ratings.{item_id}.issues must be a list of strings")
        issues = cast(list[str], raw_issues)
        unknown_issues = set(issues) - set(ISSUE_TAGS)
        if unknown_issues:
            raise ValueError(
                f"ratings.{item_id}.issues contains unknown tags: {sorted(unknown_issues)}"
            )
        ratings[item_id] = {
            "scores": _validate_scores(rating_map.get("scores", {}), item_id=item_id),
            "issues": list(dict.fromkeys(issues)),
            "note": _require_string(rating_map.get("note", ""), path=f"ratings.{item_id}.note"),
        }

    overall_defaults = empty_document()["overall"]
    overall_raw = _require_mapping(root.get("overall", {}), path="overall")
    unknown_overall = set(overall_raw) - set(overall_defaults)
    if unknown_overall:
        raise ValueError(f"overall contains unknown fields: {sorted(unknown_overall)}")
    overall: OverallData = cast(
        OverallData,
        {
            key: _require_string(overall_raw.get(key, default), path=f"overall.{key}")
            for key, default in overall_defaults.items()
        },
    )

    return copy.deepcopy(
        {
            "schema_version": 1,
            "rater": rater,
            "ratings": ratings,
            "overall": overall,
        }
    )


def _mean(scores: dict[str, float]) -> float | None:
    applicable = [score for score in scores.values() if score != -1.0]
    if not applicable:
        return None
    return fmean(applicable)


def summarize(document: ReviewDocument) -> dict[str, object]:
    """Calculate per-output, development-method, and holdout summaries."""

    outputs: list[dict[str, object]] = []
    method_values: dict[str, list[float]] = {
        "baseline": [],
        "structured": [],
        "best-of-two": [],
    }
    holdout_means: dict[str, float] = {}

    for item in REVIEW_ITEMS:
        rating = document["ratings"].get(item.item_id)
        scores = rating["scores"] if rating is not None else {}
        mean = _mean(scores)
        complete = set(scores) == set(DIMENSIONS)
        outputs.append(
            {
                "item_id": item.item_id,
                "case_id": item.case_id,
                "label": item.label,
                "method": item.method,
                "split": item.split,
                "mean": mean,
                "complete": complete,
                "scores": dict(scores),
                "issues": list(rating["issues"]) if rating is not None else [],
                "note": rating["note"] if rating is not None else "",
            }
        )
        if mean is None:
            continue
        if item.split == "development":
            method_values[item.method].append(mean)
        else:
            holdout_means[item.case_id] = mean

    development_method_means = {
        method: fmean(values) if values else None for method, values in method_values.items()
    }
    completed = sum(1 for output in outputs if output["complete"] is True)
    return {
        "outputs": outputs,
        "development_method_means": development_method_means,
        "holdout_means": holdout_means,
        "completed": completed,
        "total": len(REVIEW_ITEMS),
        "all_complete": completed == len(REVIEW_ITEMS),
    }


def _format_score(score: float | None) -> str:
    if score is None:
        return ""
    if score == -1.0:
        return "N/A"
    return f"{score:g}"


def _format_mean(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "pending"
    return f"{float(value):.4f}"


def render_csv(document: ReviewDocument) -> str:
    """Render one durable row per review output."""

    summary = summarize(document)
    output = io.StringIO(newline="")
    fields = [
        "item_id",
        "case_id",
        "candidate_label",
        "method",
        "split",
        *DIMENSIONS,
        "mean",
        "issues",
        "note",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in cast(list[dict[str, object]], summary["outputs"]):
        scores = cast(dict[str, float], row["scores"])
        writer.writerow(
            {
                "item_id": row["item_id"],
                "case_id": row["case_id"],
                "candidate_label": row["label"],
                "method": row["method"],
                "split": row["split"],
                **{dimension: _format_score(scores.get(dimension)) for dimension in DIMENSIONS},
                "mean": (
                    f"{cast(float, row['mean']):.4f}" if row["mean"] is not None else ""
                ),
                "issues": "; ".join(cast(list[str], row["issues"])),
                "note": row["note"],
            }
        )
    return output.getvalue()


def render_markdown(document: ReviewDocument) -> str:
    """Render a submission-ready attributed human-review report."""

    summary = summarize(document)
    rater = document["rater"]
    lines = [
        "# Author human-review results",
        "",
        f"- **Rater:** {rater['name'] or 'Not supplied'}",
        f"- **Review date:** {rater['review_date'] or 'Not supplied'}",
        f"- **Review type:** {rater['review_type'] or 'Author human review'}",
        (
            "- **Disclosure:** This is an attributed author sanity check, "
            "not independent or multi-rater evaluation."
        ),
        "",
        "## Per-output ratings",
        "",
        (
            "| Output | Method | Color | Print/logo | Silhouette/length | Construction | "
            "Texture/material | Presence | Mean | Main issue |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in cast(list[dict[str, object]], summary["outputs"]):
        scores = cast(dict[str, float], row["scores"])
        issue_parts = cast(list[str], row["issues"])
        note = cast(str, row["note"])
        issue = ", ".join(issue_parts)
        if note:
            issue = f"{issue}: {note}" if issue else note
        lines.append(
            "| "
            + " | ".join(
                [
                    f"{row['case_id']} — {row['method']}",
                    cast(str, row["method"]),
                    *[_format_score(scores.get(dimension)) or "—" for dimension in DIMENSIONS],
                    _format_mean(row["mean"]),
                    issue.replace("|", "\\|") or "—",
                ]
            )
            + " |"
        )

    lines.extend(["", "## Development method means", ""])
    method_means = cast(dict[str, object], summary["development_method_means"])
    for method in ("baseline", "structured", "best-of-two"):
        lines.append(f"- **{method}:** {_format_mean(method_means[method])}")

    lines.extend(["", "## Frozen holdouts", ""])
    holdouts = cast(dict[str, float], summary["holdout_means"])
    for case_id in ("H01", "H02"):
        lines.append(f"- **{case_id}:** {_format_mean(holdouts.get(case_id))}")

    overall = document["overall"]
    lines.extend(
        [
            "",
            "## Overall judgments",
            "",
            (
                "1. **Structured consistently outperformed baseline:** "
                f"{overall['structured_outperformed'] or 'Pending'}"
            ),
            f"   - {overall['structured_reason'] or 'No reason supplied.'}",
            (
                "2. **Best-of-two consistently outperformed baseline:** "
                f"{overall['best_of_two_outperformed'] or 'Pending'}"
            ),
            f"   - {overall['best_of_two_reason'] or 'No reason supplied.'}",
            (
                "3. **Any output ready for brand-critical catalog use:** "
                f"{overall['brand_critical_ready'] or 'Pending'}"
            ),
            f"   - {overall['brand_critical_reason'] or 'No reason supplied.'}",
            (
                "4. **Automatic-perfect outputs contained obvious errors:** "
                f"{overall['automatic_perfect_errors'] or 'Pending'}"
            ),
            f"   - {overall['automatic_perfect_examples'] or 'No examples supplied.'}",
            f"5. **Preferred development method:** {overall['preferred_method'] or 'Pending'}",
            f"   - {overall['preferred_method_reason'] or 'No reason supplied.'}",
            "",
            f"Completed outputs: **{summary['completed']}/{summary['total']}**.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_json(document: ReviewDocument) -> str:
    """Render validated ratings plus calculated summaries."""

    return json.dumps(
        {"review": document, "summary": summarize(document)},
        indent=2,
        sort_keys=True,
    ) + "\n"
