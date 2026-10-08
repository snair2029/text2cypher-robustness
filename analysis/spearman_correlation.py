"""
Descriptive associations between text metrics and revised evidence.

Does not use historical classifier flags or treat uncertainty as no error.
Reviewed comparisons are a selected, AI-assisted subset, not ground truth.
"""

from pathlib import Path
import pandas as pd
from scipy.stats import spearmanr

PROJECT = Path(__file__).resolve().parents[1]
INPUT = PROJECT / "outputs/evaluation_results.csv"
OUTPUT = PROJECT / "outputs/spearman_results.csv"

METRICS = [
    "bleu_score",
    "exact_match",
    "case_sensitive_trimmed_exact_match",
]


def run_spearman_correlation():
    df = pd.read_csv(INPUT, dtype=str).fillna("")

    required = {
        "instance_id",
        "syntax_generated_status",
        "manual_logical_review_status",
        *METRICS,
    }
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {sorted(missing)}")

    if df["instance_id"].str.strip().eq("").any():
        raise SystemExit("Missing instance IDs.")
    if df["instance_id"].duplicated().any():
        raise SystemExit("Duplicate instance IDs.")

    for metric in METRICS:
        raw = df[metric]
        numeric = pd.to_numeric(raw, errors="coerce")

        if (raw.ne("") & numeric.isna()).any():
            raise SystemExit(f"Invalid numeric values in {metric}.")

        valid_values = numeric.dropna()
        if metric == "bleu_score":
            if not valid_values.between(0, 100).all():
                raise SystemExit("BLEU values outside 0–100.")
        elif not valid_values.isin([0, 1]).all():
            raise SystemExit(f"Invalid binary values in {metric}.")

        df[metric] = numeric

    validation = pd.read_csv(
        PROJECT / "outputs/human_validation.csv",
        dtype=str,
    ).fillna("")

    if validation["instance_id"].duplicated().any():
        raise ValueError("Duplicate human-validation IDs.")
    if not set(validation["instance_id"]).issubset(set(df["instance_id"])):
        raise ValueError("Unknown human-validation IDs.")

    df = df.merge(
        validation[["instance_id", "logical_assessment"]],
        on="instance_id",
        how="left",
        validate="one_to_one",
    )

    # Unknown outcomes remain missing, rather than becoming zero.
    targets = {
        "neo4j_syntax_error": (
            df["syntax_generated_status"].map(
                {
                    "accepted": 0,
                    "syntax_error": 1,
                }
            ),
            "All records with accepted or syntax_error status",
            "Only two syntax errors were observed; association is fragile.",
        ),
        "validation_review_logical_error": (
            df["logical_assessment"].map(
                {
                    "error_present": 1,
                    "no_error_identified": 0,
                }
            ),
            "Determinate logical assessments in the 40-case stratified sample",
            "Student-verified AI-assisted review. Uncertain cases excluded; "
            "no_error_identified is limited to recorded interpretation rules. "
            "This is not independent ground truth or a population estimate.",
        ),
        "reviewed_error_vs_acceptable_alternative": (
            df["manual_logical_review_status"].map(
                {
                    "confirmed_generated_error_under_recorded_rules": 1,
                    "acceptable_output_alternative": 0,
                }
            ),
            "Selected flagged cases with a binary review decision",
            "AI-assisted review; 0 means acceptable output alternative, "
            "not universally proven correct. Uncertain and unreviewed "
            "cases are excluded. Results cannot be generalised to all 200.",
        ),
    }

    rows = []

    for target_name, (target, scope, limitation) in targets.items():
        for metric in METRICS:
            pairs = pd.DataFrame(
                {
                    "metric": df[metric],
                    "target": target,
                }
            ).dropna()

            rho = None
            if len(pairs) < 3:
                status = "not_computed_insufficient_pairs"
            elif pairs["metric"].nunique() < 2:
                status = "not_computed_constant_metric"
            elif pairs["target"].nunique() < 2:
                status = "not_computed_constant_target"
            else:
                rho = float(spearmanr(pairs["metric"], pairs["target"]).statistic)
                status = "descriptive_only"

            rows.append(
                {
                    "metric": metric,
                    "target": target_name,
                    "paired_records": len(pairs),
                    "excluded_records": len(df) - len(pairs),
                    "target_1_records": int(pairs["target"].eq(1).sum()),
                    "target_0_records": int(pairs["target"].eq(0).sum()),
                    "spearman_rho": rho,
                    "analysis_status": status,
                    "scope": scope,
                    "limitation": limitation,
                    "inference": "No significance or accuracy claim",
                }
            )

    results = pd.DataFrame(rows)

    print("DESCRIPTIVE SPEARMAN ASSOCIATIONS")
    print(
        results[
            [
                "metric",
                "target",
                "paired_records",
                "target_1_records",
                "target_0_records",
                "spearman_rho",
                "analysis_status",
            ]
        ]
        .round(4)
        .to_string(index=False)
    )

    print("\nINTERPRETATION")
    print("Negative rho: higher text scores tend to accompany target 0.")
    print("Positive rho: higher text scores tend to accompany target 1.")
    print("Rho near zero indicates weak rank association in this subset.")
    print("Association does not establish causation or metric reliability.")
    print("Constant variables have no defined Spearman correlation.")
    print("Schema and performance are not complete binary error labels.")
    print("No overall any-error correlation is calculated.")
    print("No p-values are presented as population-wide evidence.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".csv.tmp")
    results.to_csv(temporary, index=False)
    temporary.replace(OUTPUT)

    print(f"\nSaved: {OUTPUT}")
    print("Original queries, reviews and diagnostic files were not changed.")


if __name__ == "__main__":
    run_spearman_correlation()
