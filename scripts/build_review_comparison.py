"""Summarise the same verified 40-case reviews without changing decisions."""

from pathlib import Path
import json, hashlib
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = Path(__file__).resolve().parents[1]
paths = [
    p / "outputs/human_validation.csv",
    p / "outputs/gemma_40_review/gemma_40_human_validation.csv",
]
a, b = [
    pd.read_csv(path, keep_default_na=False).sort_values("review_order")
    for path in paths
]
for d in [a, b]:
    if len(d) != 40 or d.instance_id.duplicated().any():
        raise ValueError("Expected 40 unique reviews")
    if not d.verification_status.isin(["verified", "student_verified"]).all():
        raise ValueError("All student reviews must be verified")
if a.instance_id.tolist() != b.instance_id.tolist():
    raise ValueError("Review selections/orders differ")
rows = []
for field in [
    "syntax_assessment",
    "schema_assessment",
    "logical_assessment",
    "reference_assessment",
]:
    valid = (
        {"issue_identified", "no_issue_identified", "uncertain"}
        if field == "reference_assessment"
        else {"error_present", "no_error_identified", "uncertain"}
    )
    for name, d in [("Gemini", a), ("Gemma", b)]:
        if not d[field].isin(valid).all():
            raise ValueError("Invalid assessment: " + field)
        for label in sorted(valid):
            rows.append(
                {
                    "assessment": field,
                    "model": name,
                    "decision": label,
                    "cases": int(d[field].eq(label).sum()),
                    "denominator": 40,
                }
            )
out = p / "outputs/benchmark_comparison"
out.mkdir(parents=True, exist_ok=True)
counts = pd.DataFrame(rows)
counts.to_csv(out / "verified_40_review_counts.csv", index=False)
a[["instance_id", "review_order", "logical_assessment"]].merge(
    b[["instance_id", "logical_assessment"]],
    on="instance_id",
    suffixes=("_gemini", "_gemma"),
    validate="one_to_one",
).to_csv(out / "paired_40_logical_reviews.csv", index=False)
chart = counts[counts.assessment.eq("logical_assessment")].pivot(
    index="decision", columns="model", values="cases"
)[["Gemini", "Gemma"]]
ax = chart.rename(index=lambda s: s.replace("_", " ")).plot.barh(
    figsize=(9, 4), color=["#2369a1", "#d4782a"]
)
ax.set_xlabel("Selected questions (40 per model)")
ax.set_ylabel("")
ax.set_xlim(0, 40)
ax.set_title("Logical assessments on the same verified 40-question sample")
for c in ax.containers:
    ax.bar_label(c, padding=3)
plt.gcf().text(
    0.02,
    0.015,
    "Student-verified assessments with assistance; not independent ground truth or an overall 200-query correctness rate.",
    fontsize=8,
)
plt.tight_layout(rect=(0, 0.05, 1, 1))
for ext in ["png", "pdf"]:
    plt.savefig(out / f"verified_40_logical_reviews.{ext}", dpi=220)
plt.close()
(out / "review_provenance.json").write_text(
    json.dumps(
        {
            "inputs": {
                str(path.relative_to(p)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in paths
            },
            "same_selection_and_order": True,
            "student_verified_per_model": 40,
            "method": "Retained source review methods; no independent adjudication",
        },
        indent=2,
    )
)
print(chart.to_string())
print("PASS: same 40 IDs/order; all student verification recorded.")
