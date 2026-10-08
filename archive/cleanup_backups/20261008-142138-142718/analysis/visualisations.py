"""
Create report figures from revised evaluation evidence.

Exports 300 dpi PNGs, vector PDFs and figure captions.
Historical classifier flags are not used.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
OUTPUTS = PROJECT / "outputs"
FIGURES = OUTPUTS / "final_figures"
GROUPS = ["simple", "medium", "complex"]

BLUE = "#426782"
TEAL = "#64867D"
RUST = "#A46B55"
GREY = "#ADB4BA"
INK = "#28343D"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "axes.edgecolor": "#BCC3C8",
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

captions = []


def read_unique(filename):
    frame = pd.read_csv(OUTPUTS / filename, keep_default_na=False)
    if frame["instance_id"].duplicated().any():
        raise ValueError(f"Duplicate IDs: {filename}")
    if frame["instance_id"].eq("").any():
        raise ValueError(f"Missing IDs: {filename}")
    return frame


def save_figure(fig, name, caption):
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIGURES / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    captions.append({"figure": name, "caption": caption})
    print("Saved:", name)


def horizontal_counts(ax, series, labels, title):
    counts = series.value_counts().reindex(labels, fill_value=0)
    positions = np.arange(len(counts))
    colours = [
        RUST if "error" in name or "mismatch" in name else BLUE
        for name in counts.index
    ]
    ax.barh(positions, counts.values, color=colours, height=0.65)
    ax.set_yticks(positions)
    ax.set_yticklabels([labels[name] for name in counts.index])
    ax.invert_yaxis()
    ax.set_title(title, loc="left", pad=12)
    ax.set_xlabel("Records")
    ax.set_xlim(0, max(1, counts.max()) * 1.18)
    ax.grid(axis="x", color="#E6EAED", linewidth=0.6)
    ax.set_axisbelow(True)
    for position, count in zip(positions, counts.values):
        ax.text(count + max(1, counts.max()) * 0.02,
                position, str(count), va="center")


def boxplot_with_points(ax, values, labels, colours):
    boxes = ax.boxplot(
        values,
        patch_artist=True,
        showfliers=False,
        widths=0.48,
        medianprops={"color": INK, "linewidth": 1.6},
        whiskerprops={"color": "#7B858C"},
        capprops={"color": "#7B858C"},
    )
    for box, colour in zip(boxes["boxes"], colours):
        box.set_facecolor(colour)
        box.set_alpha(0.35)

    random = np.random.default_rng(20261002)
    for position, group in enumerate(values, 1):
        jitter = random.uniform(-0.11, 0.11, len(group))
        ax.scatter(
            position + jitter, group,
            s=16, color=colours[position - 1],
            alpha=0.55, edgecolors="none", zorder=3,
        )

    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Sentence BLEU")
    ax.set_ylim(-2, 103)
    ax.grid(axis="y", color="#E6EAED", linewidth=0.6)
    ax.set_axisbelow(True)


def plot_evaluation_coverage(df):
    fig, axes = plt.subplots(3, 1, figsize=(9, 12))
    horizontal_counts(
        axes[0], df["syntax_generated_status"],
        {
            "accepted": "Accepted",
            "syntax_error": "Syntax error",
        },
        "A. Neo4j syntax validation",
    )
    horizontal_counts(
        axes[1], df["logical_status"],
        {
            "source_graph_unavailable": "Source graph unavailable",
            "observed_result_match": "Observed result match",
            "output_shape_differs_needs_review": "Output shape differs",
            "observed_result_difference": "Observed result difference",
            "both_empty_inconclusive": "Both empty: inconclusive",
            "result_limit_inconclusive": "Row limit: inconclusive",
            "reference_defect_needs_review": "Reference defect flagged",
            "generated_syntax_error": "Generated syntax error",
            "timeout_inconclusive": "Timeout: inconclusive",
        },
        "B. Logical comparison outcomes",
    )
    horizontal_counts(
        axes[2], df["schema_generated_endpoint_status"],
        {
            "no_explicit_typed_pattern_detected": "No explicit typed pattern detected",
            "detected_simple_endpoints_supported": "Detected simple endpoints supported",
            "candidate_endpoint_mismatch_needs_review": "Endpoint mismatch candidates",
            "endpoint_schema_unavailable": "Endpoint schema unavailable",
            "partial_endpoint_check": "Partial endpoint check",
        },
        "C. Preliminary endpoint-check coverage",
    )
    fig.suptitle("Evaluation outcomes and coverage · 200 queries",
                 fontsize=14, x=0.05, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.96], h_pad=2.8)
    save_figure(
        fig, "figure_01_evaluation_coverage",
        "Recorded outcomes for 200 queries. Syntax acceptance is not answer "
        "correctness. Logical agreement is specific to the evaluated graph. "
        "Endpoint checks cover simple detected patterns; other cases remain "
        "outside that check or unresolved.",
    )


def plot_bleu_by_group(df):
    values = [
        df.loc[df["complexity"].eq(group), "bleu_score"].to_numpy()
        for group in GROUPS
    ]
    labels = [
        f"{group.capitalize()}\n(n={len(value)})"
        for group, value in zip(GROUPS, values)
    ]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    boxplot_with_points(ax, values, labels, [BLUE, TEAL, GREY])
    ax.set_title("BLEU by question-length group", loc="left", pad=14)
    ax.set_xlabel("Question-length group")
    fig.tight_layout()
    save_figure(
        fig, "figure_02_bleu_by_question_length",
        "Sentence BLEU distributions for 50 simple, 100 medium and 50 complex "
        "question-length groups. Boxes show quartiles and medians; whiskers "
        "follow the 1.5-IQR convention. Points show all observations, with "
        "horizontal jitter for visibility. These groups are not validated "
        "measures of query difficulty.",
    )


def plot_bleu_by_review(df):
    statuses = [
        "confirmed_generated_error_under_recorded_rules",
        "acceptable_output_alternative",
        "reviewed_without_final_binary_label",
    ]
    values = [
        df.loc[df["manual_logical_review_status"].eq(status),
               "bleu_score"].to_numpy()
        for status in statuses
    ]
    labels = [
        f"Recorded-rule error\n(n={len(values[0])})",
        f"Acceptable alternative\n(n={len(values[1])})",
        f"Unresolved\n(n={len(values[2])})",
    ]
    fig, ax = plt.subplots(figsize=(8, 5))
    boxplot_with_points(ax, values, labels, [RUST, TEAL, GREY])
    ax.set_title("BLEU across reconciled flagged-case reviews",
                 loc="left", pad=14)
    fig.tight_layout()
    save_figure(
        fig, "figure_03_bleu_by_review_outcome",
        "BLEU for the 48 selected comparison cases: 10 recorded-rule errors, "
        "8 acceptable output alternatives and 30 without a final binary label. "
        "Reviews were AI-assisted. Selection was based on comparison differences; "
        "these distributions cannot establish a dataset-wide error rate. "
        "Acceptable output variation is not universal proof of correctness.",
    )


def plot_human_review(validation):
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for ax, category in zip(
        axes.flat, ["syntax", "schema", "logical", "reference"]
    ):
        if category == "reference":
            outcomes = ["no_issue_identified", "issue_identified", "uncertain"]
        else:
            outcomes = ["no_error_identified", "error_present", "uncertain"]
        counts = validation[f"{category}_assessment"].value_counts()
        values = [int(counts.get(outcome, 0)) for outcome in outcomes]
        ax.bar(range(3), values, color=[TEAL, RUST, GREY], width=0.6)
        ax.set_xticks(range(3))
        ax.set_xticklabels(["No issue\nidentified", "Issue\nidentified", "Uncertain"])
        ax.set_title(category.capitalize(), loc="left")
        ax.set_ylabel("Reviewed records")
        ax.set_ylim(0, 44)
        ax.grid(axis="y", color="#E6EAED", linewidth=0.6)
        ax.set_axisbelow(True)
        for position, count in enumerate(values):
            ax.text(position, count + 0.8, str(count), ha="center")

    fig.suptitle("Student-verified, AI-assisted review · 40 cases",
                 fontsize=14, x=0.06, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.94], h_pad=2)
    save_figure(
        fig, "figure_04_validation_assessments",
        "Assessments for the stratified 40-case sample: 10 simple, 20 medium "
        "and 10 complex questions. Student verification used AI proposals "
        "and some prior evidence; this is not independent blinded validation. "
        "No issue identified is limited to the stated assessment rules.",
    )


def plot_performance():
    summary = pd.read_csv(OUTPUTS / "performance_profile_summary.csv")
    keys = ["instance_id", "database", "query_kind"]
    if summary.duplicated(keys).any():
        raise ValueError("Duplicate performance summary rows.")

    matched = summary["all_repetitions_nonempty_result_match"].astype(
        str
    ).str.lower().eq("true")
    if not matched.all() or not summary["repetitions"].eq(3).all():
        raise ValueError("Performance summary contains non-comparable cases.")

    metrics = ["db_hits_median", "client_elapsed_profile_ms_median"]
    wide = summary.pivot(
        index=["instance_id", "database"],
        columns="query_kind",
        values=metrics,
    )
    if wide.isna().any().any():
        raise ValueError("Incomplete performance pairs.")

    comparison = pd.DataFrame(index=wide.index)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 5))

    for ax, metric, title in zip(
        axes,
        metrics,
        ["Database hits", "Client elapsed time with PROFILE (ms)"],
    ):
        reference = wide[(metric, "reference")]
        generated = wide[(metric, "generated")]
        comparison[f"reference_{metric}"] = reference
        comparison[f"generated_{metric}"] = generated
        comparison[f"generated_to_reference_{metric}"] = (
            generated / reference.replace(0, np.nan)
        )

        ax.scatter(reference, generated, s=30, color=BLUE,
                   alpha=0.7, edgecolors="white", linewidths=0.4)
        limit = max(float(reference.max()), float(generated.max()), 1) * 1.15
        ax.plot([0, limit], [0, limit], color="#87939B",
                linestyle="--", linewidth=1)
        ax.set_xscale("symlog", linthresh=1)
        ax.set_yscale("symlog", linthresh=1)
        ax.set_xlim(0, limit)
        ax.set_ylim(0, limit)
        ax.set_xlabel("Reference query")
        ax.set_ylabel("Generated query")
        ax.set_title(title, loc="left", pad=12)
        ax.grid(color="#E6EAED", linewidth=0.5)
        ax.set_axisbelow(True)

    comparison.reset_index().to_csv(
        OUTPUTS / "performance_comparison.csv", index=False
    )
    fig.suptitle(f"Paired performance measurements · {len(wide)} query pairs",
                 fontsize=14, x=0.06, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_figure(
        fig, "figure_05_paired_performance",
        f"Median measurements from three repetitions per query for {len(wide)} "
        "previously matching pairs. Warm-ups excluded. All measured repetitions "
        "returned non-empty matching results under the recorded comparator. "
        "Dashed lines indicate equal measurements; axes use symmetric logarithmic "
        "scales with a linear region near zero. Database hits sum plan-operator "
        "hits. Client timing includes network transfer and PROFILE overhead. "
        "These are session-specific comparisons, not binary inefficiency labels.",
    )


def run_visualisations():
    df = read_unique("evaluation_results.csv")
    validation = read_unique("human_validation.csv")

    if len(df) != 200 or len(validation) != 40:
        raise ValueError("Expected 200 evaluation records and 40 review cases.")

    df["bleu_score"] = pd.to_numeric(df["bleu_score"], errors="raise")
    if not df["bleu_score"].between(0, 100).all():
        raise ValueError("BLEU outside 0–100.")

    plot_evaluation_coverage(df)
    plot_bleu_by_group(df)
    plot_bleu_by_review(df)
    plot_human_review(validation)
    plot_performance()

    pd.DataFrame(captions).to_csv(
        FIGURES / "figure_captions.csv", index=False
    )
    print("\nFive figures exported as PNG and PDF.")
    print("Captions:", FIGURES / "figure_captions.csv")
    print("Historical figures were not deleted or used as evidence.")
    print("Original queries and diagnostic files were not changed.")


if __name__ == "__main__":
    run_visualisations()
