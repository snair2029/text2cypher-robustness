"""Display saved Gemini–Gemma evidence without generating or executing queries."""

from pathlib import Path
import pandas as pd
import streamlit as st


def load_csv(path: Path):
    """Load current saved evidence, preserving blank fields."""
    return pd.read_csv(path, keep_default_na=False)


def show_figure(path: Path):
    """A missing exported figure must not hide its underlying evidence."""
    if path.exists():
        st.image(str(path), width="stretch")
    else:
        st.info(f"Figure unavailable: {path.name}. Saved tables remain available.")


def download_csv(path: Path, label=None):
    if path.exists():
        st.download_button(
            label or path.name,
            path.read_bytes(),
            file_name=path.name,
            mime="text/csv",
            key="comparison_download_" + path.name,
        )


def _show_overview(metrics):
    for col, (_, row) in zip(st.columns(2), metrics.iterrows()):
        with col:
            st.subheader(row["model"])
            st.metric("Mean sentence BLEU", f"{row['mean_sentence_bleu']:.4f}")
            st.metric(
                "Trimmed Exact Match",
                f"{int(row['case_sensitive_trimmed_exact_match_count'])}/200",
            )
            st.metric(
                "Neo4j syntax accepted", f"{int(row['syntax_accepted_count'])}/200"
            )
    st.caption(
        "BLEU averages saved sentence scores over all 200 queries, including zeros. Exact Match is case-sensitive after trimming. Lowercase Exact Match is 14/200 for each model. Text similarity and syntax acceptance do not establish query correctness."
    )


def _show_outcomes(folder, counts):
    st.subheader("Database evaluation outcomes")
    display = counts.rename(columns={"logical_status": "Saved outcome"}).copy()
    display["Saved outcome"] = (
        display["Saved outcome"].str.replace("_", " ").str.capitalize()
    )
    with st.expander("View exact outcome counts"):
        st.dataframe(display, hide_index=True, width="stretch")
    show_figure(folder / "logical_outcomes.png")
    st.info(
        "Each model has 89 source-graph-unavailable outcomes, but only 88 are the same questions. Syntax failures can be recorded before graph checks. Unavailable and inconclusive cases are retained, and public graphs were not immutable snapshots."
    )
    st.subheader("Paired reference-result agreement")
    show_figure(folder / "paired_matches.png")
    st.caption(
        "An observed match means agreement with the reference on the tested graph. “Neither observed match” includes unavailable, review and inconclusive cases; it is not a count of incorrect answers."
    )


def _show_examples(project, pairs):
    st.subheader("Inspect the same question")
    gemini = load_csv(project / "data/generated_queries.csv").set_index("instance_id")
    gemma = load_csv(project / "outputs/benchmark_gemma_26b.csv").set_index(
        "instance_id"
    )
    search = st.text_input(
        "Search questions",
        placeholder="Question text or instance ID",
        key="benchmark_search",
    )
    available = gemini.loc[pairs.instance_id, "question"]
    if search:
        available = available[
            available.str.contains(search, case=False, regex=False)
            | available.index.to_series().str.contains(search, case=False, regex=False)
        ]
    if available.empty:
        st.info("No questions match your search.")
        return
    selected = st.selectbox(
        "Question",
        available.index.tolist(),
        format_func=lambda value: f"{available.loc[value]} · {value}",
        key="benchmark_question",
    )
    st.write(gemini.loc[selected, "question"])
    with st.expander("Supplied schema"):
        st.code(gemini.loc[selected, "schema"])
    st.code(gemini.loc[selected, "cypher"], language="cypher")
    st.caption("Dataset reference query")
    evidence = pairs.set_index("instance_id").loc[selected]
    for col, name, df, suffix in zip(
        st.columns(2), ["Gemini", "Gemma"], [gemini, gemma], ["gemini", "gemma"]
    ):
        with col:
            st.subheader(name)
            st.code(df.loc[selected, "generated_cypher"], language="cypher")
            st.write(
                "Saved outcome: "
                + evidence["logical_status_" + suffix].replace("_", " ")
            )
            with st.expander("Saved execution evidence"):
                for key in [
                    "generated_row_count",
                    "reference_row_count",
                    "generated_error",
                    "reference_error",
                    "generated_preview",
                    "reference_preview",
                ]:
                    st.write(key.replace("_", " ").capitalize() + ":")
                    st.text(str(evidence.get(key + "_" + suffix, "")))


def _show_reviews(project, folder):
    review_counts_path = folder / "verified_40_review_counts.csv"
    if review_counts_path.exists():
        st.subheader("Same 40-question review sample")
        st.caption(
            "The same question IDs and order were inspected for both models. Student verification is recorded; source assistance disclosures remain. Uncertain decisions are retained. This selected sample is not independent ground truth or overall accuracy."
        )
        st.dataframe(load_csv(review_counts_path), hide_index=True, width="stretch")
        show_figure(folder / "verified_40_logical_reviews.png")

    with st.expander("Additional Gemma flagged-case review"):
        review_path = project / "outputs/gemma_26b_logical_review.csv"
        if review_path.exists():
            reviews = load_csv(review_path)
            st.subheader("Gemma flagged-case review")
            st.caption(
                "AI-assisted inspection of 47 flagged cases using queries, supplied schemas and saved previews. No independent adjudication or database rerun; these are not an overall correctness rate."
            )
            st.dataframe(
                reviews.final_review_decision.value_counts()
                .rename_axis("Decision")
                .reset_index(name="Cases"),
                hide_index=True,
            )
            selected_review = st.selectbox(
                "Flagged question ID",
                reviews.instance_id.tolist(),
                key="flagged_question",
            )
            chosen = reviews.set_index("instance_id").loc[selected_review]
            st.write("Review: " + chosen.final_review_decision.replace("_", " "))
            st.write(chosen.review_reason)
            if "student_verification_status" in reviews:
                st.caption(
                    "Recorded student verification: "
                    + str(chosen.student_verification_status).replace("_", " ")
                )


def _show_performance(folder):
    performance_path = folder / "performance_comparison_summary.csv"
    if performance_path.exists():
        st.subheader("Saved query performance")
        performance = load_csv(performance_path)
        st.dataframe(
            performance.rename(
                columns={
                    "model": "Model",
                    "common_cases": "Common questions",
                    "median_db_hits": "Median database hits",
                    "median_recorded_client_profile_ms": "Median recorded client PROFILE time (ms)",
                }
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Only common questions with three measured repetitions and nonempty reference agreement are included. Warm-ups are excluded. Runs occurred at different times; client timing includes network transfer and PROFILE overhead. This does not measure model generation speed or establish a controlled latency difference."
        )
        figure = folder / "performance_comparison.png"
        if figure.exists():
            show_figure(figure)
        with st.expander("Paired performance measurements"):
            paired_path = folder / "paired_performance_measurements.csv"
            if paired_path.exists():
                st.dataframe(load_csv(paired_path), hide_index=True, width="stretch")
                st.download_button(
                    "Download paired performance records",
                    paired_path.read_bytes(),
                    file_name=paired_path.name,
                    mime="text/csv",
                    key="download_performance_pairs",
                )


def _show_downloads(folder):
    st.subheader("Download comparison evidence")
    st.caption("CSV files contain the saved values used in the charts and tables.")
    names = [
        "model_metrics.csv",
        "logical_outcome_counts.csv",
        "paired_match_counts.csv",
        "paired_outcome_crosstab.csv",
        "paired_logical_outcomes.csv",
        "verified_40_review_counts.csv",
        "paired_40_logical_reviews.csv",
        "performance_comparison_summary.csv",
        "paired_performance_measurements.csv",
    ]
    columns = st.columns(2)
    for index, name in enumerate(names):
        with columns[index % 2]:
            download_csv(folder / name)


def show_benchmark(project: Path):
    folder = project / "outputs/benchmark_comparison"
    required = [
        "model_metrics.csv",
        "logical_outcome_counts.csv",
        "paired_logical_outcomes.csv",
        "paired_match_counts.csv",
    ]
    missing = [name for name in required if not (folder / name).exists()]
    if missing:
        st.warning("Comparison evidence is incomplete: " + ", ".join(missing))
        return
    st.header("Gemini versus Gemma")
    st.write(
        "Compare saved responses to the same 200 questions, schemas and reference queries."
    )
    with st.expander("Models and comparison method"):
        st.write(
            "Gemini 3.1 Flash Lite is recorded in the journal and generation script; "
            "per-query model metadata was not retained. Gemma records gemma-4-26b-a4b-it. "
            "Provider generation defaults were not explicitly controlled. "
            "This comparison describes the recorded runs."
        )
    try:
        metrics = load_csv(folder / "model_metrics.csv")
        counts = load_csv(folder / "logical_outcome_counts.csv")
        pairs = load_csv(folder / "paired_logical_outcomes.csv")
    except (OSError, ValueError, pd.errors.ParserError) as error:
        st.error(f"Could not load saved comparison evidence: {error}")
        return
    tabs = st.tabs(
        [
            "Overview",
            "Database outcomes",
            "Compare a question",
            "Review evidence",
            "Query performance",
            "Downloads",
        ]
    )
    renderers = [
        lambda: _show_overview(metrics),
        lambda: _show_outcomes(folder, counts),
        lambda: _show_examples(project, pairs),
        lambda: _show_reviews(project, folder),
        lambda: _show_performance(folder),
        lambda: _show_downloads(folder),
    ]
    for tab, render in zip(tabs, renderers):
        with tab:
            try:
                render()
            except (OSError, ValueError, KeyError, pd.errors.ParserError) as error:
                st.error(f"This evidence section could not be loaded: {error}")
