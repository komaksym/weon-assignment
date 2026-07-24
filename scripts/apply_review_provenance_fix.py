from pathlib import Path


def replace(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text()
    if old not in text:
        raise SystemExit(f"missing expected text in {path}: {old!r}")
    file.write_text(text.replace(old, new))


# Reviewer-neutral reusable output schema.
replace(
    "src/weon_eval/reporting.py",
    '''def manual_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:\n    return [\n        {\n            "case_id": row["case_id"],\n            "strategy": row["strategy"],\n            **{dimension: "" for dimension in ATTRIBUTE_DIMENSIONS},\n            "mean_manual_score": "",\n            "selector_agrees": "" if row["strategy"] == "best_of_two" else "n/a",\n            "notes": "",\n        }\n        for row in rows\n    ]\n''',
    '''def review_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:\n    """Create a reviewer-attributed visual-assessment scaffold."""\n\n    return [\n        {\n            "case_id": row["case_id"],\n            "strategy": row["strategy"],\n            "reviewer": "",\n            "review_method": "",\n            **{dimension: "" for dimension in ATTRIBUTE_DIMENSIONS},\n            "mean_review_score": "",\n            "selector_agrees": "" if row["strategy"] == "best_of_two" else "n/a",\n            "notes": "",\n        }\n        for row in rows\n    ]\n''',
)
replace("src/weon_eval/development.py", "    manual_rows,\n", "    review_rows,\n")
replace(
    "src/weon_eval/development.py",
    'write_csv(output_root / "manual_scores.csv", manual_rows(rows))',
    'write_csv(output_root / "review_scores.csv", review_rows(rows))',
)
replace(
    "src/weon_eval/holdout.py",
    '''def _manual_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:\n    return [\n        {\n            "case_id": row["case_id"],\n            "strategy": "baseline",\n            **{dimension: "" for dimension in ATTRIBUTE_DIMENSIONS},\n            "mean_manual_score": "",\n            "notes": "",\n        }\n        for row in rows\n    ]\n''',
    '''def _review_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:\n    """Create a reviewer-attributed visual-assessment scaffold."""\n\n    return [\n        {\n            "case_id": row["case_id"],\n            "strategy": "baseline",\n            "reviewer": "",\n            "review_method": "",\n            **{dimension: "" for dimension in ATTRIBUTE_DIMENSIONS},\n            "mean_review_score": "",\n            "notes": "",\n        }\n        for row in rows\n    ]\n''',
)
replace(
    "src/weon_eval/holdout.py",
    'write_csv(output_root / "manual_scores.csv", _manual_rows(rows))',
    'write_csv(output_root / "review_scores.csv", _review_rows(rows))',
)
replace(
    "src/weon_eval/holdout.py",
    '"status": "frozen - pending manual sanity check",',
    '"status": "frozen - pending reviewer-attributed visual assessment",',
)

# Tests make the neutral schema and old-name removal explicit.
replace(
    "tests/test_development.py",
    '''    rows = list(csv.DictReader((output_root / "results.csv").open()))\n    assert len(rows) == 9\n''',
    '''    rows = list(csv.DictReader((output_root / "results.csv").open()))\n    assert len(rows) == 9\n    review_rows = list(csv.DictReader((output_root / "review_scores.csv").open()))\n    assert len(review_rows) == 9\n    assert all(row["reviewer"] == "" for row in review_rows)\n    assert all(row["review_method"] == "" for row in review_rows)\n    assert all(row["mean_review_score"] == "" for row in review_rows)\n    assert not (output_root / "manual_scores.csv").exists()\n''',
)
replace(
    "tests/test_holdout.py",
    '''    rows = list(csv.DictReader((output_root / "results.csv").open()))\n    assert [row["case_id"] for row in rows] == ["H01", "H02"]\n''',
    '''    rows = list(csv.DictReader((output_root / "results.csv").open()))\n    assert [row["case_id"] for row in rows] == ["H01", "H02"]\n    review_rows = list(csv.DictReader((output_root / "review_scores.csv").open()))\n    assert [row["case_id"] for row in review_rows] == ["H01", "H02"]\n    assert all(row["reviewer"] == "" for row in review_rows)\n    assert all(row["review_method"] == "" for row in review_rows)\n    assert all(row["mean_review_score"] == "" for row in review_rows)\n    assert not (output_root / "manual_scores.csv").exists()\n''',
)

# Committed score provenance and filenames.
old = Path("experiments/slice-3-manual-scores.csv")
new = Path("experiments/slice-3-chatgpt-visual-scores.csv")
text = old.read_text().replace(
    "case_id,strategy,color,print_logo,silhouette_length,construction_details,texture_material,presence,mean_manual_score,selector_agrees,notes",
    "case_id,strategy,reviewer,review_method,color,print_logo,silhouette_length,construction_details,texture_material,presence,mean_review_score,selector_agrees,notes",
)
lines = text.splitlines()
lines[1:] = [
    line.replace(",baseline,", ",baseline,ChatGPT,visual assessment of contact sheet,", 1)
    .replace(",structured,", ",structured,ChatGPT,visual assessment of contact sheet,", 1)
    .replace(",best_of_two,", ",best_of_two,ChatGPT,visual assessment of contact sheet,", 1)
    for line in lines[1:]
]
new.write_text("\n".join(lines) + "\n")
old.unlink()

old = Path("experiments/slice-4-holdout-manual.csv")
new = Path("experiments/slice-4-holdout-chatgpt-visual-scores.csv")
text = old.read_text().replace(
    "case_id,strategy,color,print_logo,silhouette_length,construction_details,texture_material,presence,mean_manual_score,notes",
    "case_id,strategy,reviewer,review_method,color,print_logo,silhouette_length,construction_details,texture_material,presence,mean_review_score,notes",
)
lines = text.splitlines()
lines[1:] = [
    line.replace(
        ",baseline,",
        ",baseline,ChatGPT,visual assessment of crop-enhanced contact sheet,",
        1,
    )
    for line in lines[1:]
]
new.write_text("\n".join(lines) + "\n")
old.unlink()

# Public-facing result language.
replacements = {
    "README.md": [
        ("development manual mean", "development ChatGPT visual-assessment mean"),
        ("holdout manual mean", "holdout ChatGPT visual-assessment mean"),
        ("applicability validation and human audit", "applicability validation and a separate review path"),
        ("Blinded VLM + human review", "Blinded VLM + ChatGPT visual assessment"),
    ],
    "REPORT.md": [
        ("manual means were", "ChatGPT visual-assessment means were"),
        ("manual scores were", "ChatGPT visual-assessment scores were"),
        ("the human reviewer preferred B", "the ChatGPT visual assessment preferred B"),
        ("A manual sanity check uses", "A separate ChatGPT visual assessment uses"),
        ("Manual mean", "ChatGPT visual-assessment mean"),
        ("did not improve the manual aggregate", "did not improve the ChatGPT visual-assessment aggregate"),
        ("manually strongest", "highest-scoring in the ChatGPT visual assessment"),
        ("| Automatic | Manual |", "| Automatic | ChatGPT visual assessment |"),
        ("audited against human judgment", "audited through a separate review path"),
    ],
    "PLANS.md": [
        ("manual garment inspection", "ChatGPT visual inspection"),
        ("Manual means were", "ChatGPT visual-assessment means were"),
        ("human review alongside", "ChatGPT visual assessment alongside"),
        ("The manual mean is", "The ChatGPT visual-assessment mean is"),
        ("automatic/manual CSV evidence", "automatic/ChatGPT visual-assessment CSV evidence"),
        ("human judgments", "ChatGPT visual judgments"),
        ("manual-score change", "ChatGPT visual-score change"),
    ],
    "experiments/D01-baseline.md": [
        ("## Manual inspection", "## ChatGPT visual inspection"),
    ],
    "experiments/slice-3-development.md": [
        ("manual review favored", "the ChatGPT visual assessment favored"),
        ("Manual mean", "ChatGPT visual-assessment mean"),
        ("## Manual sanity check", "## ChatGPT visual assessment"),
        ("Human selector assessment", "ChatGPT selector assessment"),
        ("human disagreement", "ChatGPT-assessment disagreement"),
        ("manual aggregate", "ChatGPT visual-assessment aggregate"),
        ("manual rubric", "visual-assessment rubric"),
        ("manual winner", "ChatGPT visual-assessment leader"),
    ],
    "experiments/slice-4-holdout.md": [
        ("| Automatic | Manual |", "| Automatic | ChatGPT visual assessment |"),
        ("manual-score change", "ChatGPT visual-score change"),
        ("manually strongest", "highest-scoring in the ChatGPT visual assessment"),
    ],
    "spec.md": [
        ("Manual garment inspection", "Reviewer-attributed garment inspection"),
        ("## 8. Manual inspection", "## 8. Reviewer-attributed visual inspection"),
        ("concise manual inspection evidence", "concise visual-inspection evidence and reviewer provenance"),
        (
            "the image is manually inspected against the references",
            "the image is visually inspected against the references with reviewer provenance recorded",
        ),
    ],
    "specs/slice-3-development-experiments.md": [
        (
            "`manual_scores.csv` with the same rubric and selector-agreement field",
            "`review_scores.csv` with the same rubric plus reviewer, method, and selector-agreement fields",
        ),
        ("## Manual sanity check", "## Reviewer-attributed visual assessment"),
        (
            "score all nine strategy rows manually",
            "declare the reviewer and method, then score all nine strategy rows",
        ),
        (
            "compare blinded automatic and manual strategy means",
            "compare blinded automatic and reviewer-attributed strategy means",
        ),
    ],
    "specs/slice-4-holdout-submission.md": [
        ("a manual-score template", "a reviewer-attributed score template"),
        (
            "Inspect both holdouts manually",
            "Visually assess both holdouts and record reviewer identity and method",
        ),
        (
            "`experiments/slice-4-holdout-manual.csv`: completed human sanity check",
            "`experiments/slice-4-holdout-chatgpt-visual-scores.csv`: completed ChatGPT visual assessment; no independent human reviewer participated",
        ),
    ],
}
for path, pairs in replacements.items():
    for old_text, new_text in pairs:
        replace(path, old_text, new_text)

# Explicit provenance and limitation statements.
replace(
    "README.md",
    "- holdout generation latency: `13.1647 s` total.\n",
    "- holdout generation latency: `13.1647 s` total.\n\n"
    "The visual-assessment scores were assigned by ChatGPT from the contact sheets. "
    "No independent human evaluator participated, so these scores are supplemental "
    "AI-generated evidence rather than human validation.\n",
)
replace(
    "README.md",
    "Each holdout contact sheet contains",
    "The development and holdout commands emit reviewer-neutral `review_scores.csv` "
    "templates. The committed filled assessments are explicitly named "
    "`*-chatgpt-visual-scores.csv`.\n\nEach holdout contact sheet contains",
)
replace(
    "REPORT.md",
    "![Development comparison](submission/figures/development-comparison.jpg)\n",
    "![Development comparison](submission/figures/development-comparison.jpg)\n\n"
    "**Reviewer provenance:** the second visual-assessment path was performed by ChatGPT "
    "from the committed contact sheets. No independent human reviewer participated. "
    "These scores are therefore an AI-generated qualitative cross-check, not human validation.\n",
)
replace(
    "REPORT.md",
    "A separate ChatGPT visual assessment uses the same six dimensions.",
    "A separate ChatGPT visual assessment uses the same six dimensions. It is a distinct "
    "AI judgment path, not an independent human evaluation.",
)
replace(
    "REPORT.md",
    "The baseline was frozen because it was simplest, cheapest, fastest, and highest-scoring in the ChatGPT visual assessment.",
    "The baseline was frozen primarily because the blinded automatic comparison tied while "
    "baseline was simplest, cheapest, and fastest. Its small lead in the ChatGPT visual "
    "assessment was treated only as supplemental evidence.",
)
replace(
    "REPORT.md",
    "The main methodological lesson is that automatic evaluation must be blinded, applicability-validated, and audited through a separate review path.",
    "The main methodological lesson is that automatic evaluation must be blinded, "
    "applicability-validated, and audited through a separate review path. This experiment "
    "still lacks independent human evaluation, which remains a key limitation before "
    "production conclusions are drawn.",
)
replace(
    "experiments/D01-baseline.md",
    "## ChatGPT visual inspection\n",
    "## ChatGPT visual inspection\n\nChatGPT performed this inspection from the generated "
    "artifact and references. No independent human reviewer participated.\n",
)
replace(
    "experiments/slice-3-development.md",
    "## ChatGPT visual assessment\n",
    "## ChatGPT visual assessment\n\nChatGPT assigned these scores from the contact sheets. "
    "They are a separate AI judgment path, not independent human evaluation.\n",
)
replace(
    "experiments/slice-3-development.md",
    "The blinded automatic comparison provides no strategy advantage.",
    "The blinded automatic comparison provides no strategy advantage. Baseline selection is "
    "operationally justified by lower cost, latency, and complexity; the ChatGPT "
    "visual-assessment lead is supplemental rather than human-grounded evidence.",
)
replace(
    "experiments/slice-4-holdout.md",
    "## Results\n",
    "## Results\n\nThe qualitative scores below were assigned by ChatGPT from the "
    "crop-enhanced contact sheets. No independent human reviewer participated.\n",
)
replace(
    "experiments/slice-4-holdout.md",
    "The baseline remains the final method because development comparisons showed no blinded automatic advantage for structured prompting or best-of-two, while baseline was cheaper, faster, and highest-scoring in the ChatGPT visual assessment.",
    "The baseline remains the final method because development comparisons showed no blinded "
    "automatic advantage for structured prompting or best-of-two, while baseline was cheaper "
    "and faster. The ChatGPT visual-assessment scores are supplemental and are not presented "
    "as human validation.",
)
replace(
    "PLANS.md",
    "## Constraints honored\n",
    "## Evaluation provenance\n\nThe completed visual-assessment scores were produced by "
    "ChatGPT from the contact sheets. No independent human evaluator participated; this is an "
    "explicit limitation of the evidence.\n\n## Constraints honored\n",
)
replace(
    "spec.md",
    "Inspect the result against all three D01 references.\n",
    "Inspect the result against all three D01 references and record the reviewer identity and "
    "method. In the completed run, ChatGPT performed this visual inspection; no independent "
    "human reviewer participated.\n",
)

# Ensure old schema/file claims are gone from tracked source and evidence.
forbidden = (
    "mean_manual_score",
    "slice-3-manual-scores.csv",
    "slice-4-holdout-manual.csv",
    "independent human visual review",
    "Human selector assessment",
    "## Manual sanity check",
    "## Manual inspection",
)
this_file = Path(__file__).resolve()
for file in Path(".").rglob("*"):
    if (
        not file.is_file()
        or ".git" in file.parts
        or file.resolve() == this_file
        or file.suffix not in {".md", ".py", ".csv"}
    ):
        continue
    text = file.read_text(errors="ignore")
    for phrase in forbidden:
        if phrase in text:
            raise SystemExit(f"misleading legacy phrase remains in {file}: {phrase}")
