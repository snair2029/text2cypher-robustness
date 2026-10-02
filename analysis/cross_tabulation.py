"""
Summarise revised evaluation evidence by question-length group.

Uses assembled results, preserves uncertainty and excludes historical
classifier flags from final outcome counts. Group percentages describe
recorded outcomes, not overall correctness.
"""

from pathlib import Path
import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
OUTPUTS = PROJECT / "outputs"
INPUT = OUTPUTS / "evaluation_results.csv"
GROUPS = ["simple", "medium", "complex"]

STAGES = {
    "syntax": "syntax_generated_status",
    "schema_names": "schema_generated_name_coverage_status",
    "schema_properties": "schema_generated_property_name_status",
    "logical_comparison": "logical_status",
    "logical_review": "manual_logical_review_status",
    "performance_plan": "performance_status",
}


def save_csv(frame, path):
    temporary = path.with_suffix(".csv.tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def run_cross_tabulation():
    df = pd.read_csv(INPUT, dtype=str).fillna("")

    required = {
        "instance_id", "complexity", "bleu_score", "exact_match",
        "case_sensitive_trimmed_exact_match", *STAGES.values(),
    }
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {sorted(missing)}")

    if df["instance_id"].str.strip().eq("").any():
        raise SystemExit("Missing instance IDs.")
    if df["instance_id"].duplicated().any():
        raise SystemExit("Duplicate instance IDs.")

    df["complexity"] = df["complexity"].str.strip().str.lower()
    unexpected = set(df["complexity"]) - set(GROUPS)
    if unexpected:
        raise SystemExit(f"Unexpected groups: {sorted(unexpected)}")

    df["bleu_score"] = pd.to_numeric(df["bleu_score"], errors="coerce")
    if df["bleu_score"].isna().any():
        raise SystemExit("Missing or invalid BLEU scores; inspect before analysis.")
    if not df["bleu_score"].between(0, 100).all():
        raise SystemExit("BLEU scores outside 0–100.")

    metric_columns = [
        "exact_match", "case_sensitive_trimmed_exact_match"
    ]
    for column in metric_columns:
        values = df[column]
        invalid = ~values.isin(["", "0", "1", "0.0", "1.0"])
        if invalid.any():
            raise SystemExit(f"Invalid binary values in {column}.")
        df[column] = pd.to_numeric(values, errors="coerce")

    output_rows = []

    print("REVISED EVALUATION SUMMARY")
    print("Groups describe question length, not proven query difficulty.")

    for stage, column in STAGES.items():
        outcomes = df[column].replace("", "not_recorded")
        table = pd.crosstab(df["complexity"], outcomes).reindex(
            GROUPS, fill_value=0
        )
        print(f"\n{stage.upper()}")
        print(table.to_string())

        for group in GROUPS:
            subset = df.loc[df["complexity"].eq(group)]
            counts = subset[column].replace(
                "", "not_recorded"
            ).value_counts()

            for outcome, count in counts.items():
                output_rows.append({
                    "stage": stage,
                    "question_length_group": group,
                    "outcome": outcome,
                    "records": int(count),
                    "group_records": len(subset),
                    "percent_of_group": round(
                        100 * count / len(subset), 2
                    ),
                })

    metric_rows = []
    for group in GROUPS + ["all"]:
        subset = (
            df if group == "all"
            else df.loc[df["complexity"].eq(group)]
        )
        scores = subset["bleu_score"]

        row = {
            "question_length_group": group,
            "records": len(subset),
            "bleu_records": int(scores.count()),
            "bleu_mean": scores.mean(),
            "bleu_median": scores.median(),
            "bleu_std": scores.std(),
        }

        for column in metric_columns:
            values = subset[column].dropna()
            row[column + "_assessable"] = len(values)
            row[column + "_count"] = int(values.sum())
            row[column + "_percent"] = (
                100 * values.mean() if len(values) else None
            )

        metric_rows.append(row)

    metrics = pd.DataFrame(metric_rows)
    print("\nTEXT METRICS")
    print(metrics.round(4).to_string(index=False))

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    save_csv(
        pd.DataFrame(output_rows),
        OUTPUTS / "cross_tabulation.csv",
    )
    save_csv(metrics, OUTPUTS / "bleu_by_complexity.csv")

    print("\nINTERPRETATION")
    print("Outcome percentages use all records in each stated group.")
    print("Unavailable, inconclusive and unreviewed cases remain visible.")
    print("The 48-case review was selected for comparison differences.")
    print("Its reviewed errors are not an overall logical-error rate.")
    print("Schema-name coverage does not establish complete schema validity.")
    print("Plan inspection does not establish measured efficiency.")
    print("Historical Exact Match lowercases and trims query text.")
    print("The added Exact Match preserves case and trims query text.")
    print("Neither text metric establishes answer correctness.")
    print("The separate partial 40-case AI-assisted review is not included.")

    print("\nSaved: outputs/cross_tabulation.csv")
    print("Saved: outputs/bleu_by_complexity.csv")
    print("Original queries and diagnostic evidence were not changed.")


if __name__ == "__main__":
    run_cross_tabulation()
