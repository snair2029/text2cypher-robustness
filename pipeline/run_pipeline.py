"""
Assemble saved evaluation evidence into one results table.

This command validates record coverage and combines existing outputs.
It does not generate queries or rerun database evaluations.
Original data and diagnostic files are never modified.
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
OUTPUTS = PROJECT / "outputs"

INPUT = PROJECT / "data/generated_queries.csv"
COMBINED = OUTPUTS / "evaluation_results.csv"
SUMMARY = OUTPUTS / "evaluation_summary.json"

SOURCES = {
    "syntax": OUTPUTS / "neo4j_syntax_validation.csv",
    "schema": OUTPUTS / "schema_inventory.csv",
    "logical": OUTPUTS / "logical_validation.csv",
    "performance": OUTPUTS / "performance_validation.csv",
}

REQUIRED_COLUMNS = {
    "syntax": ["generated_status", "reference_status"],
    "schema": [
        "schema_status",
        "generated_name_coverage_status",
        "generated_property_name_status",
    ],
    "logical": ["logical_status"],
    "performance": ["performance_status"],
}

LEGACY_COLUMNS = [
    "syntax_error",
    "syntax_error_msg",
    "schema_hallucination",
    "schema_hallucination_msg",
    "logical_error",
    "logical_error_msg",
    "performance_error",
    "performance_error_msg",
]


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_checked(path):
    if not path.is_file():
        raise ValueError(f"Required file missing: {path}")

    frame = pd.read_csv(path)

    if "instance_id" not in frame.columns:
        raise ValueError(f"No instance_id column: {path.name}")

    if frame["instance_id"].isna().any():
        raise ValueError(f"Missing instance IDs: {path.name}")

    if frame["instance_id"].duplicated().any():
        raise ValueError(f"Duplicate instance IDs: {path.name}")

    return frame


def counts(frame, column):
    return {
        str(key): int(value)
        for key, value in frame[column].fillna("not_recorded").value_counts().items()
    }


def save_csv(frame, path):
    temporary = path.with_suffix(".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def read_logical_reviews(expected_ids, logical_results):
    """Validate saved reviews without changing their decisions."""
    path = OUTPUTS / "manual_review.csv"

    if not path.is_file():
        raise ValueError(f"Required review register missing: {path}")

    reviews = pd.read_csv(path, dtype=str).fillna("")

    required = {
        "instance_id",
        "review_stage",
        "review_decision",
        "generated_logical_error",
        "review_reason",
        "review_method",
        "reviewed_at_utc",
    }

    required.update(
        {
            "final_review_decision",
            "final_generated_logical_error",
            "reconciliation_notes",
            "reconciliation_method",
            "reconciled_at_utc",
        }
    )

    missing = required - set(reviews.columns)
    if missing:
        raise ValueError(f"Review register: missing columns {sorted(missing)}")

    if reviews["instance_id"].str.strip().eq("").any():
        raise ValueError("Review register contains missing instance IDs.")

    if reviews.duplicated(["instance_id", "review_stage"]).any():
        raise ValueError("Review register contains duplicate ID/stage entries.")

    unknown_ids = set(reviews["instance_id"]) - expected_ids
    if unknown_ids:
        raise ValueError(f"Review register contains unknown IDs: {sorted(unknown_ids)}")

    logical_reviews = reviews.loc[reviews["review_stage"].eq("logical")].copy()

    labels = logical_reviews["final_generated_logical_error"]
    if not labels.isin(["", "0", "1"]).all():
        raise ValueError("Logical review labels must be blank, 0 or 1.")

    for column in [
        "review_decision",
        "review_reason",
        "review_method",
        "reviewed_at_utc",
    ]:
        if logical_reviews[column].str.strip().eq("").any():
            raise ValueError(f"Logical reviews contain missing {column}.")

    error_decision = logical_reviews["final_review_decision"].eq(
        "confirmed_generated_logical_error"
    )
    acceptable_decision = logical_reviews["final_review_decision"].eq(
        "acceptable_output_alternative"
    )

    if not error_decision.equals(labels.eq("1")):
        raise ValueError("Confirmed-error decisions and labels disagree.")

    if not acceptable_decision.equals(labels.eq("0")):
        raise ValueError("Acceptable-alternative decisions and labels disagree.")

    candidates = set(
        logical_results.loc[
            logical_results["logical_status"].isin(
                [
                    "output_shape_differs_needs_review",
                    "observed_result_difference",
                ]
            ),
            "instance_id",
        ]
    )
    reviewed_ids = set(logical_reviews["instance_id"])
    missing_reviews = candidates - reviewed_ids

    if missing_reviews:
        raise ValueError(
            f"{len(missing_reviews)} comparison cases still need review notes."
        )

    review_summary = {
        "register_records": len(logical_reviews),
        "flagged_comparison_cases": len(candidates),
        "flagged_comparison_cases_reviewed": len(candidates & reviewed_ids),
        "flagged_comparison_cases_without_review": len(missing_reviews),
        "confirmed_generated_errors_under_recorded_rules": int(labels.eq("1").sum()),
        "acceptable_output_alternatives": int(labels.eq("0").sum()),
        "without_final_binary_label": int(labels.eq("").sum()),
        "decision_counts": counts(logical_reviews, "final_review_decision"),
        "method": (
            "AI-assisted inspection of queries, supplied schemas and saved "
            "previews; independent adjudication has not been established."
        ),
        "interpretation": (
            "Review counts describe the reviewed subset. They are not an "
            "overall correctness or logical-error rate for the full dataset."
        ),
        "register_sha256": fingerprint(path),
    }

    # Keep reviewed labels distinct from historical classifier labels.
    renamed = logical_reviews.drop(columns=["review_stage"]).rename(
        columns={
            column: "manual_" + column
            for column in logical_reviews.columns
            if column not in ["instance_id", "review_stage"]
        }
    )

    return renamed, review_summary


def run_full_pipeline():
    print("ASSEMBLING SAVED EVALUATION EVIDENCE", flush=True)

    queries = read_checked(INPUT)
    expected_ids = set(queries["instance_id"])
    diagnostics = {}

    # Validate every input before writing any combined output.
    for stage, path in SOURCES.items():
        frame = read_checked(path)

        missing_columns = set(REQUIRED_COLUMNS[stage]) - set(frame.columns)
        if missing_columns:
            raise ValueError(f"{stage}: missing columns {sorted(missing_columns)}")

        missing_ids = expected_ids - set(frame["instance_id"])
        extra_ids = set(frame["instance_id"]) - expected_ids

        if missing_ids or extra_ids:
            raise ValueError(
                f"{stage}: {len(missing_ids)} missing IDs, "
                f"{len(extra_ids)} unexpected IDs."
            )

        diagnostics[stage] = frame
        print(f"{stage}: {len(frame)} records, IDs match", flush=True)

    combined = queries.rename(
        columns={
            column: "legacy_" + column
            for column in LEGACY_COLUMNS
            if column in queries.columns
        }
    )

    for stage, frame in diagnostics.items():
        renamed = frame.rename(
            columns={
                column: (
                    column if column.startswith(stage + "_") else stage + "_" + column
                )
                for column in frame.columns
                if column != "instance_id"
            }
        )

        collisions = (set(combined.columns) & set(renamed.columns)) - {"instance_id"}

        if collisions:
            raise ValueError(f"{stage}: conflicting columns {sorted(collisions)}")

        combined = combined.merge(
            renamed,
            on="instance_id",
            how="left",
            validate="one_to_one",
            sort=False,
        )

    manual_reviews, manual_summary = read_logical_reviews(
        expected_ids, diagnostics["logical"]
    )

    collisions = (set(combined.columns) & set(manual_reviews.columns)) - {"instance_id"}
    if collisions:
        raise ValueError(f"Manual reviews: conflicting columns {sorted(collisions)}")

    combined = combined.merge(
        manual_reviews,
        on="instance_id",
        how="left",
        validate="one_to_one",
        sort=False,
    )

    # A blank binary label can mean unresolved or not reviewed.
    # This separate status makes that distinction visible.
    reviewed = combined["manual_final_review_decision"].notna()
    labels = combined["manual_final_generated_logical_error"].fillna("")

    combined["manual_logical_review_status"] = "not_reviewed"
    combined.loc[reviewed, "manual_logical_review_status"] = (
        "reviewed_without_final_binary_label"
    )
    combined.loc[reviewed & labels.eq("1"), "manual_logical_review_status"] = (
        "confirmed_generated_error_under_recorded_rules"
    )
    combined.loc[reviewed & labels.eq("0"), "manual_logical_review_status"] = (
        "acceptable_output_alternative"
    )

    total = len(combined)

    if total == 0:
        raise ValueError("No queries available.")

    # Keep the dataset's existing Exact Match field unchanged.
    # Add an explicit, case-sensitive text comparison.
    valid = (
        combined["cypher"].notna()
        & combined["generated_cypher"].notna()
        & combined["cypher"].fillna("").str.strip().ne("")
        & combined["generated_cypher"].fillna("").str.strip().ne("")
    )

    strict_match = pd.Series(pd.NA, index=combined.index, dtype="Int64")
    strict_match.loc[valid] = (
        combined.loc[valid, "cypher"].str.strip()
        == combined.loc[valid, "generated_cypher"].str.strip()
    ).astype(int)

    combined["case_sensitive_trimmed_exact_match"] = strict_match

    alias = combined["database_reference_alias"]
    has_alias = alias.notna() & alias.fillna("").str.strip().ne("")

    summary = {
        "assembled_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "assemble_saved_evaluations",
        "manual_logical_review": manual_summary,
        "total_records": total,
        "records_with_source_graph_alias": int(has_alias.sum()),
        "records_without_source_graph_alias": int((~has_alias).sum()),
        "generated_syntax_status": counts(diagnostics["syntax"], "generated_status"),
        "reference_syntax_status": counts(diagnostics["syntax"], "reference_status"),
        "generated_schema_name_status": counts(
            diagnostics["schema"], "generated_name_coverage_status"
        ),
        "generated_property_name_status": counts(
            diagnostics["schema"], "generated_property_name_status"
        ),
        "logical_status": counts(diagnostics["logical"], "logical_status"),
        "performance_status": counts(diagnostics["performance"], "performance_status"),
        "case_sensitive_trimmed_exact_match_count": int(strict_match.sum()),
        "exact_match_assessable_records": int(valid.sum()),
        "input_sha256": fingerprint(INPUT),
        "diagnostic_sha256": {
            stage: fingerprint(path) for stage, path in SOURCES.items()
        },
        "limitations": [
            "Matching IDs establish coverage, not freshness of evaluations.",
            "Hashes identify the files assembled in this run; they do not "
            "prove which inputs produced earlier diagnostic outputs.",
            "Schema checks are preliminary and do not fully resolve "
            "property ownership, scope or dynamic expressions.",
            "Observed execution agreement applies to current live graphs "
            "and is not proof of correctness.",
            "Automatic logical review categories remain preliminary.",
            "Manual decisions are AI-assisted review findings; independent "
            "adjudication has not been established.",
            "Unresolved and unreviewed cases are not counted as correct.",
            "Review records are linked by ID; their original query versions "
            "were not fingerprinted when the decisions were recorded.",
            "EXPLAIN does not measure runtime or database work.",
            "Legacy classifier labels are retained as historical evidence "
            "and are not used as validated error counts.",
        ],
    }

    logical = diagnostics["logical"]
    if "logical_review_category" in logical.columns:
        summary["logical_review_categories"] = counts(
            logical, "logical_review_category"
        )

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    save_csv(combined, COMBINED)

    temporary = SUMMARY.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    temporary.replace(SUMMARY)

    print("\nASSEMBLY COMPLETE")
    print(f"Combined records: {total}")
    print(
        "Records with source graph aliases:",
        summary["records_with_source_graph_alias"],
    )

    print("\nGENERATED SYNTAX STATUS")
    print(diagnostics["syntax"]["generated_status"].value_counts().to_string())

    print("\nLOGICAL STATUS")
    print(logical["logical_status"].value_counts().to_string())

    print("\nSAVED LOGICAL REVIEW")
    print(
        "Review entries:",
        manual_summary["register_records"],
    )
    print(
        "Confirmed errors under recorded rules:",
        manual_summary["confirmed_generated_errors_under_recorded_rules"],
    )
    print(
        "Acceptable alternatives:",
        manual_summary["acceptable_output_alternatives"],
    )
    print(
        "Without a final binary label:",
        manual_summary["without_final_binary_label"],
    )
    print(
        "Comparison cases without review:",
        manual_summary["flagged_comparison_cases_without_review"],
    )

    print("\nPERFORMANCE PLAN STATUS")
    print(diagnostics["performance"]["performance_status"].value_counts().to_string())

    print(f"\nResults: {COMBINED}")
    print(f"Summary: {SUMMARY}")
    print("Original queries and diagnostic files were not changed.")
    print("Database evaluations were not rerun.")
    print(
        "Reconciled review evidence assembled. PROFILE measurements are saved separately."
    )


if __name__ == "__main__":
    run_full_pipeline()
