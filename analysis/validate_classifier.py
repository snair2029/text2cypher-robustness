"""
Audit the 40-case student-verified, AI-assisted validation sample.

Checks that reviewed question/query/schema text matches the source.
Reports assessment coverage and comparisons with automatic evidence.
Syntax agreement metrics apply only to determinate paired assessments.
No overall correctness or independent validation claim is made.
"""

from pathlib import Path
import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
OUTPUTS = PROJECT / "outputs"
CATEGORIES = ("syntax", "schema", "logical", "reference")


def read_checked(path):
    frame = pd.read_csv(path, keep_default_na=False)
    if "instance_id" not in frame:
        raise ValueError(f"Missing instance_id: {path.name}")
    if frame["instance_id"].eq("").any():
        raise ValueError(f"Missing ID: {path.name}")
    if frame["instance_id"].duplicated().any():
        raise ValueError(f"Duplicate ID: {path.name}")
    return frame


def run_validation():
    reviews = read_checked(OUTPUTS / "human_validation.csv")
    queries = read_checked(PROJECT / "data/generated_queries.csv")
    syntax = read_checked(OUTPUTS / "neo4j_syntax_validation.csv")
    schema = read_checked(OUTPUTS / "schema_inventory.csv")
    logical = read_checked(OUTPUTS / "logical_validation.csv")

    if len(reviews) != 40:
        raise ValueError(f"Expected 40 selected cases; found {len(reviews)}.")

    assessment_fields = [f"{category}_assessment" for category in CATEGORIES]
    required = assessment_fields + ["review_reason", "reviewer"]
    for column in required:
        if column not in reviews or reviews[column].str.strip().eq("").any():
            raise ValueError(f"Incomplete review field: {column}")

    allowed = {
        "syntax": {"no_error_identified", "error_present", "uncertain"},
        "schema": {"no_error_identified", "error_present", "uncertain"},
        "logical": {"no_error_identified", "error_present", "uncertain"},
        "reference": {"no_issue_identified", "issue_identified", "uncertain"},
    }
    for category in CATEGORIES:
        invalid = set(reviews[f"{category}_assessment"]) - allowed[category]
        if invalid:
            raise ValueError(f"Unexpected {category} values: {sorted(invalid)}")

    expected_groups = {"simple": 10, "medium": 20, "complex": 10}
    if reviews["complexity"].value_counts().to_dict() != expected_groups:
        raise ValueError("Review group counts do not match the selected sample.")

    # Verify the reviewed material, rather than relying on IDs alone.
    original = queries.set_index("instance_id")
    if not set(reviews["instance_id"]).issubset(original.index):
        raise ValueError("A reviewed ID is missing from the source queries.")

    for _, row in reviews.iterrows():
        source = original.loc[row["instance_id"]]
        for review_column, source_column in (
            ("question", "question"),
            ("schema", "schema"),
            ("reference_cypher", "cypher"),
            ("generated_cypher", "generated_cypher"),
            ("complexity", "complexity"),
        ):
            if str(row[review_column]) != str(source[source_column]):
                raise ValueError(
                    f"Reviewed material changed: {row['instance_id']} "
                    f"({review_column})."
                )

    result = reviews.copy()
    evidence = (
        (syntax, ["generated_status"], "automatic_syntax_"),
        (
            schema,
            [
                "generated_name_coverage_status",
                "generated_property_name_status",
            ],
            "automatic_schema_",
        ),
        (logical, ["logical_status"], "automatic_"),
    )

    for frame, columns, prefix in evidence:
        if set(frame["instance_id"]) != set(queries["instance_id"]):
            raise ValueError("Automatic evidence does not cover the source IDs.")
        selected = frame[["instance_id"] + columns].rename(
            columns={column: prefix + column for column in columns}
        )
        result = result.merge(
            selected, on="instance_id", validate="one_to_one", how="left"
        )

    print("40-CASE VALIDATION AUDIT")
    print("Reviewed material matches the source queries and schemas.")
    print("\nREVIEW COVERAGE")
    print(result["complexity"].value_counts().to_string())

    for category in CATEGORIES:
        print(f"\n{category.upper()} ASSESSMENTS")
        print(result[f"{category}_assessment"].value_counts().to_string())

    print("\nSYNTAX COMPARISON")
    print(
        pd.crosstab(
            result["syntax_assessment"],
            result["automatic_syntax_generated_status"],
        ).to_string()
    )

    human = result["syntax_assessment"].map(
        {
            "no_error_identified": 0,
            "error_present": 1,
        }
    )
    automatic = result["automatic_syntax_generated_status"].map(
        {
            "accepted": 0,
            "syntax_error": 1,
        }
    )
    paired = human.notna() & automatic.notna()
    truth = human[paired]
    prediction = automatic[paired]

    tp = int(((truth == 1) & (prediction == 1)).sum())
    tn = int(((truth == 0) & (prediction == 0)).sum())
    fp = int(((truth == 0) & (prediction == 1)).sum())
    fn = int(((truth == 1) & (prediction == 0)).sum())

    def ratio(numerator, denominator):
        return f"{numerator / denominator:.3f}" if denominator else "undefined"

    print(f"\nDeterminate syntax pairs: {int(paired.sum())}/40")
    print(f"TP={tp}, TN={tn}, FP={fp}, FN={fn}")
    print("Agreement:", ratio(tp + tn, int(paired.sum())))
    print("Precision:", ratio(tp, tp + fp))
    print("Recall:", ratio(tp, tp + fn))
    print(
        "These are descriptive agreement metrics against the recorded "
        "assessments, not independent accuracy estimates."
    )

    print("\nSCHEMA NAME CHECK VS STUDENT SCHEMA ASSESSMENT")
    print(
        pd.crosstab(
            result["schema_assessment"],
            result["automatic_schema_generated_name_coverage_status"],
        ).to_string()
    )

    print("\nLOGICAL EVIDENCE VS STUDENT LOGICAL ASSESSMENT")
    print(
        pd.crosstab(
            result["logical_assessment"],
            result["automatic_logical_status"],
        ).to_string()
    )

    result["validation_method"] = (
        "Student-verified AI-assisted review; not independent blinded validation"
    )

    target = OUTPUTS / "classifier_validation.csv"
    backup = OUTPUTS / "classifier_validation.historical_audit.csv"
    if target.exists() and not backup.exists():
        backup.write_bytes(target.read_bytes())

    temporary = target.with_name(target.name + ".tmp")
    result.to_csv(temporary, index=False)
    temporary.replace(target)

    print("\nINTERPRETATION")
    print("Uncertain assessments remain separate from binary outcomes.")
    print("No error identified is limited to the stated review rules.")
    print("Schema-name coverage cannot detect every endpoint or type defect.")
    print("Logical result disagreement is not automatically a generated error.")
    print("Unavailable graphs are not treated as correct predictions.")
    print("Reviews used AI assistance and some prior evaluation evidence.")
    print("Performance was not assessed by this human review.")
    print(f"\nSaved: {target}")
    print("Original queries, review decisions and diagnostics were not changed.")


if __name__ == "__main__":
    run_validation()
