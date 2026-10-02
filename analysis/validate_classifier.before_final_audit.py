"""
Audit historical human labels against the revised evaluation evidence.

This is a coverage and comparison report, not a classifier accuracy
estimate. Historical labels are preserved. AI-assisted review decisions
are not treated as independent predictions or human ground truth.
"""

from pathlib import Path
import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
INPUT = PROJECT / "outputs/evaluation_results.csv"
OUTPUT = PROJECT / "outputs/classifier_validation.csv"

EVIDENCE_COLUMNS = [
    "syntax_generated_status",
    "schema_generated_name_coverage_status",
    "schema_generated_property_name_status",
    "logical_status",
    "performance_status",
    "manual_review_decision",
    "manual_generated_logical_error",
    "manual_review_reason",
    "manual_review_method",
]

HISTORICAL_COLUMNS = [
    "legacy_syntax_error",
    "legacy_schema_hallucination",
    "legacy_logical_error",
    "legacy_performance_error",
]


def run_validation():
    if not INPUT.is_file():
        raise SystemExit(
            "Combined results are missing. Run "
            "python pipeline/run_pipeline.py first."
        )

    data = pd.read_csv(INPUT, dtype=str).fillna("")

    required = {"instance_id", "manual_label", "logical_status"}
    missing = required - set(data.columns)
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")

    if data["instance_id"].str.strip().eq("").any():
        raise SystemExit("Missing instance IDs.")
    if data["instance_id"].duplicated().any():
        raise SystemExit("Duplicate instance IDs.")

    historical_labels = data["manual_label"].str.strip()
    labelled = data.loc[historical_labels.ne("")].copy()

    if labelled.empty:
        raise SystemExit("No historical human labels were found.")

    labelled["manual_label"] = labelled["manual_label"].str.strip()
    labelled["validation_scope"] = (
        "Historical labelled subset; coverage audit only"
    )
    labelled["accuracy_assessment"] = (
        "Not calculated: revised checks do not provide complete, "
        "validated predictions for all error categories"
    )

    print("HISTORICAL HUMAN-LABEL VALIDATION AUDIT")
    print("=" * 60)
    print("Total evaluation records:", len(data))
    print("Historically labelled records:", len(labelled))

    print("\nHISTORICAL LABEL DISTRIBUTION")
    print(labelled["manual_label"].value_counts().to_string())

    if "complexity" in data.columns:
        coverage = pd.DataFrame({
            "sample_records": data["complexity"].value_counts(),
            "labelled_records": labelled["complexity"].value_counts(),
        }).fillna(0).astype(int)

        coverage["labelled_percent"] = (
            100 * coverage["labelled_records"]
            / coverage["sample_records"]
        ).round(1)

        print("\nCOVERAGE BY QUESTION-LENGTH GROUP")
        print(coverage.to_string())

    if "cypher_complexity" in labelled.columns:
        print("\nRECORDED CYPHER COMPLEXITY IN LABELLED SUBSET")
        print(labelled["cypher_complexity"].value_counts().to_string())

    print("\nHISTORICAL LABELS VS AUTOMATIC LOGICAL OUTCOMES")
    print(pd.crosstab(
        labelled["manual_label"],
        labelled["logical_status"],
    ).to_string())

    if "manual_review_decision" in labelled.columns:
        review_present = labelled["manual_review_decision"].str.strip().ne("")
        print(
            "\nHistorically labelled records also included in "
            "the AI-assisted flagged-case review:",
            int(review_present.sum()),
        )
        print(
            "These reviews are contextual evidence, not independent "
            "classifier validation."
        )

    columns = [
        "instance_id", "question", "complexity", "cypher_complexity",
        "manual_label", "label_notes",
        *HISTORICAL_COLUMNS,
        *EVIDENCE_COLUMNS,
        "bleu_score", "exact_match",
        "case_sensitive_trimmed_exact_match",
        "validation_scope", "accuracy_assessment",
    ]
    columns = [column for column in columns if column in labelled.columns]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".csv.tmp")
    labelled[columns].to_csv(temporary, index=False)
    temporary.replace(OUTPUT)

    print("\nINTERPRETATION")
    print(
        "Historical labels remain available, but their labelling rules "
        "and category definitions must be checked before reuse."
    )
    print(
        "The multiple_errors label does not identify which error "
        "categories were present."
    )
    print(
        "Observed matches, unavailable graphs and inconclusive checks "
        "are not automatically converted into no_error predictions."
    )
    print(
        "Accuracy, precision and recall are not calculated by this audit."
    )
    print(f"\nSaved: {OUTPUT}")
    print("Original queries, labels and diagnostic files were not changed.")


if __name__ == "__main__":
    run_validation()
