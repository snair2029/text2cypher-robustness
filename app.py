"""A guided interface for saved Text-to-Cypher research evidence."""

from pathlib import Path
import json
import subprocess
import sys

import pandas as pd
import streamlit as st

PROJECT = Path(__file__).resolve().parent
RESULTS = PROJECT / "outputs/evaluation_results.csv"
SUMMARY = PROJECT / "outputs/evaluation_summary.json"

st.set_page_config(
    page_title="Text-to-Cypher | Research Explorer",
    page_icon="🔎",
    layout="wide",
)

st.markdown(
    """
<style>
.block-container {max-width: 1200px; padding-top: 2.5rem;}
h1 {letter-spacing: -0.035em;}
h2 {letter-spacing: -0.02em;}
[data-testid="stMetric"] {
    background: var(--secondary-background-color);
    padding: 1.1rem;
    border-radius: 12px;
    border: 1px solid rgba(128,128,128,.18);
}
.stButton button, .stDownloadButton button {border-radius: 8px;}
</style>
""",
    unsafe_allow_html=True,
)

STATUS = {
    "observed_result_match": (
        "Matching results",
        "The two queries returned matching results on the tested database. "
        "This is evidence of agreement, rather than proof that both answer "
        "the question correctly.",
    ),
    "observed_result_difference": (
        "Different results — needs review",
        "The returned values differed. Review the query meaning, ordering, "
        "numeric precision and reference quality before assigning an error.",
    ),
    "output_shape_differs_needs_review": (
        "Different output format — needs review",
        "The queries returned different numbers of columns. One may return "
        "a whole record while the other returns selected details.",
    ),
    "source_graph_unavailable": (
        "Not tested — source database unavailable",
        "This record has no mapped source database for result comparison.",
    ),
    "generated_syntax_error": (
        "Query syntax error",
        "Neo4j rejected the generated query during syntax validation.",
    ),
    "reference_defect_needs_review": (
        "Reference query needs review",
        "A previously identified reference issue prevents a reliable "
        "automatic correctness judgement.",
    ),
    "both_empty_inconclusive": (
        "No results from either query",
        "Two empty results provide insufficient evidence to establish "
        "that the generated answer is correct.",
    ),
    "result_limit_inconclusive": (
        "Comparison stopped — too many rows",
        "At least one query exceeded the evaluator's 5,000-row limit.",
    ),
    "timeout_inconclusive": (
        "Comparison stopped — time limit reached",
        "At least one query exceeded the evaluation timeout.",
    ),
    "reference_execution_failed": (
        "Reference could not be evaluated",
        "Inspect the recorded error before judging the generated query.",
    ),
    "generated_execution_failed": (
        "Generated query could not be evaluated",
        "Inspect the recorded error to determine its cause.",
    ),
}

REVIEW = {
    "projection_difference_needs_review": "Which details should be returned?",
    "projection_and_duplicate_handling_needs_review": "Should repeated answers be removed?",
    "reference_or_question_interpretation_needs_review": "Does the reference reflect the question?",
    "year_boundary_interpretation_needs_review": "How should the year boundary be interpreted?",
    "ordering_filter_or_limit_needs_review": "How should answers be filtered and ordered?",
    "aggregation_identity_needs_review": "Are separate entities being combined?",
    "pattern_filter_or_cardinality_needs_review": "Does the query follow the intended relationships?",
    "numeric_rounding_difference": "Small numeric rounding difference",
}

PERFORMANCE = {
    "plan_inspected_no_cartesian_product": "Plan inspected",
    "source_graph_unavailable": "Source database unavailable",
    "generated_syntax_error": "Syntax error — plan not inspected",
    "potential_cartesian_product_needs_review": "Potential Cartesian product — review needed",
    "generated_plan_failed": "Plan inspection failed",
    "graph_connection_failed": "Database connection failed",
}


MANUAL_REVIEW_LABELS = {
    "confirmed_generated_error_under_recorded_rules": "Generated error identified in review",
    "acceptable_output_alternative": "Acceptable way to present the answer",
    "reviewed_without_final_binary_label": "Reviewed — answer remains uncertain",
    "not_reviewed": "Outside the flagged comparison review",
}


def show_saved_review(row):
    status = text(row.get("manual_logical_review_status"))

    if not status or status == "not_reviewed":
        st.info(
            "This example was outside the 48 flagged comparison cases "
            "reviewed in this pass. Its automatic outcome remains evidence "
            "to interpret; it is not a final correctness judgement."
        )
        return

    title = readable(status, MANUAL_REVIEW_LABELS)

    if status == "confirmed_generated_error_under_recorded_rules":
        st.error(title)
    elif status == "acceptable_output_alternative":
        st.success(title)
    else:
        st.warning(title)

    st.markdown("**Why was this decision recorded?**")
    st.write(text(row.get("manual_review_reason")))
    reconciliation = text(row.get("manual_reconciliation_notes"))
    if reconciliation:
        st.markdown("**Updated interpretation**")
        st.write(reconciliation)

    st.caption(
        "These are AI-assisted findings from query inspection, the supplied "
        "schema and saved result previews. Independent adjudication has "
        "not been established. An acceptable alternative is not proof "
        "of correctness on every possible database."
    )


def text(value):
    return "" if value is None or pd.isna(value) else str(value)


def readable(value, mapping):
    value = text(value)
    return mapping.get(value, value.replace("_", " ").capitalize())


def outcome(value):
    value = text(value)
    return STATUS.get(
        value,
        (value.replace("_", " ").capitalize(), "Inspect the saved evidence."),
    )


def navigate(page, instance_id=None):
    st.session_state["page"] = page
    if instance_id:
        st.session_state["preferred_record"] = instance_id


def evidence(row, prefix):
    values = {
        column: text(row[column])
        for column in row.index
        if column.startswith(prefix) and text(row[column])
    }
    st.json(values)


def horizontal_chart(series, labels):
    records = [
        {"Outcome": labels(str(key)), "Questions": int(value)}
        for key, value in series.value_counts().items()
    ]
    st.vega_lite_chart(
        {
            "data": {"values": records},
            "mark": {
                "type": "bar",
                "color": "#2563eb",
                "cornerRadiusEnd": 4,
            },
            "encoding": {
                "y": {
                    "field": "Outcome",
                    "type": "nominal",
                    "sort": "-x",
                    "axis": {"title": None, "labelLimit": 350},
                },
                "x": {
                    "field": "Questions",
                    "type": "quantitative",
                    "axis": {"title": "Number of questions", "tickMinStep": 1},
                },
                "tooltip": [
                    {"field": "Outcome", "type": "nominal"},
                    {"field": "Questions", "type": "quantitative"},
                ],
            },
            "height": max(150, len(records) * 38),
        },
        width="stretch",
    )


pages = ["Start here", "Explore an example", "Research results", "Model comparison"]
PAGE_LABELS = {
    "Start here": "Start here",
    "Explore an example": "Gemini examples",
    "Research results": "Gemini research results",
    "Model comparison": "Gemini versus Gemma",
}

with st.sidebar:
    st.markdown("### Research Explorer")
    st.caption("Text-to-Cypher honours project")
    page = st.radio("Choose a page", pages, key="page", format_func=PAGE_LABELS.get)
    st.divider()
    st.caption(
        "Showing saved evaluation evidence. "
        "Opening a page does not generate or execute queries."
    )
    with st.expander("Researcher tools"):
        if st.button("Update combined results"):
            try:
                with st.spinner("Checking saved evaluation files..."):
                    result = subprocess.run(
                        [sys.executable, str(PROJECT / "pipeline/run_pipeline.py")],
                        cwd=PROJECT,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                if result.returncode:
                    st.error("The update failed.")
                    st.code(result.stdout + result.stderr)
                else:
                    st.rerun()
            except subprocess.TimeoutExpired:
                st.error("The update exceeded its time limit.")
        st.caption("This assembles saved files; it does not rerun evaluations.")

if page != "Model comparison":
    if not RESULTS.exists() or not SUMMARY.exists():
        st.error("Evaluation results are not available yet.")
        st.write("Run `python pipeline/run_pipeline.py` in the project terminal.")
        st.stop()

    try:
        data = pd.read_csv(RESULTS)
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    except Exception as error:
        st.error(f"Could not load the saved evaluation: {error}")
        st.stop()

    required_review_columns = {
        "manual_logical_review_status",
        "manual_review_decision",
        "manual_review_reason",
    }
    if not required_review_columns.issubset(data.columns):
        st.error("The combined results do not yet include the saved reviews.")
        st.write("Run `python pipeline/run_pipeline.py` in the project terminal.")
        st.stop()


st.caption("HONOURS RESEARCH · TEXT-TO-CYPHER")
st.title("From a question to a database query")
st.write(
    "Explore how a language model translates everyday questions into "
    "Cypher, the language used to query a graph database."
)

if page == "Start here":
    st.subheader("Explore the benchmark")
    st.write(
        "Compare Gemini and Gemma on the same 200 questions, then inspect saved queries and evaluation evidence."
    )
    st.button(
        "Compare Gemini and Gemma",
        on_click=navigate,
        args=("Model comparison",),
        type="primary",
    )
    st.caption(
        "The examples and original research results below describe the Gemini run."
    )
    st.subheader("Start with one Gemini example")
    st.write(
        "No coding knowledge is needed. Choose an example, read the "
        "question and follow what the evaluation found. Technical "
        "evidence is available when you want more detail."
    )

    columns = st.columns(3)
    examples = [
        (
            "See matching results",
            "Compare two queries that returned the same results.",
            data[data["logical_status"] == "observed_result_match"],
        ),
        (
            "Understand a query error",
            "See why Neo4j rejected a generated query.",
            data[data["syntax_generated_status"] == "syntax_error"],
        ),
        (
            "Understand a reviewed error",
            "See the recorded explanation of a query-meaning error.",
            data[
                data["manual_logical_review_status"]
                == "confirmed_generated_error_under_recorded_rules"
            ],
        ),
    ]

    for column, (title, description, subset) in zip(columns, examples):
        with column:
            with st.container(border=True):
                st.markdown("#### " + title)
                st.write(description)
                if not subset.empty:
                    st.button(
                        "Open example",
                        key=title,
                        on_click=navigate,
                        args=("Explore an example", subset.iloc[0]["instance_id"]),
                        width="stretch",
                    )

    st.subheader("What happens in the research?")
    steps = st.columns(4)
    for column, title, description in zip(
        steps,
        ["1. Ask", "2. Generate", "3. Check", "4. Interpret"],
        [
            "A dataset provides a question and a description of the graph.",
            "The saved model response contains a proposed Cypher query.",
            "Syntax, schema names, query results and plans are inspected.",
            "Evidence is compared with text metrics and reviewed.",
        ],
    ):
        with column:
            st.markdown("**" + title + "**")
            st.write(description)

    st.info(
        "This interface explores saved research results. Matching a "
        "reference answer does not automatically prove correctness."
    )

elif page == "Explore an example":
    st.subheader("Choose a question")
    left, right = st.columns([2, 1])
    with left:
        search = st.text_input(
            "Search questions",
            placeholder="Try movies, companies, tweets or an instance ID",
        )
    with right:
        statuses = sorted(data["logical_status"].dropna().unique())
        selected_status = st.selectbox(
            "Show",
            ["all"] + statuses,
            format_func=lambda value: (
                "All evaluation outcomes" if value == "all" else outcome(value)[0]
            ),
        )

    review_filter = st.selectbox(
        "Filter by saved review finding",
        ["all"] + list(MANUAL_REVIEW_LABELS),
        format_func=lambda value: (
            "All review findings" if value == "all" else MANUAL_REVIEW_LABELS[value]
        ),
    )

    filtered = data.copy()
    if review_filter != "all":
        filtered = filtered[filtered["manual_logical_review_status"] == review_filter]
    if search:
        filtered = filtered[
            filtered["question"]
            .fillna("")
            .str.contains(search, case=False, regex=False)
            | filtered["instance_id"].str.contains(search, case=False, regex=False)
        ]
    if selected_status != "all":
        filtered = filtered[filtered["logical_status"] == selected_status]

    if filtered.empty:
        st.info("No questions match. Try another search or outcome.")
        st.stop()

    ids = filtered["instance_id"].tolist()
    questions = filtered.set_index("instance_id")["question"].to_dict()
    preferred = st.session_state.pop("preferred_record", None)
    selected_id = st.selectbox(
        f"Question ({len(filtered)} available)",
        ids,
        index=ids.index(preferred) if preferred in ids else 0,
        format_func=lambda value: f"{questions[value]} · {value}",
    )
    row = filtered[filtered["instance_id"] == selected_id].iloc[0]

    st.divider()
    st.caption("STEP 1 · THE QUESTION")
    st.subheader(text(row["question"]))

    st.caption("STEP 2 · THE TWO QUERIES")
    st.write(
        "The model's query is compared with the dataset's reference. "
        "References can also contain defects or interpretation choices."
    )
    left, right = st.columns(2)
    with left:
        st.markdown("**Model-generated query**")
        st.code(text(row["generated_cypher"]), language="cypher")
    with right:
        st.markdown("**Dataset reference query**")
        st.code(text(row["cypher"]), language="cypher")

    st.caption("STEP 3 · WHAT THE CHECKS FOUND")
    title, description = outcome(row["logical_status"])
    with st.container(border=True):
        st.markdown("### " + title)
        st.write(description)

        syntax = text(row.get("syntax_generated_status"))
        st.markdown("**Can Neo4j understand the query?**")
        if syntax == "accepted":
            st.write("Yes — Neo4j accepted its syntax.")
        elif syntax == "syntax_error":
            st.write("No — a syntax error was detected.")
        else:
            st.write("See the syntax evidence for the recorded outcome.")

        st.markdown("**What was checked against the graph description?**")
        st.write(
            "Preliminary checks compare detected labels, relationship "
            "types and property names with the supplied schema. They do "
            "not fully validate property ownership or query meaning."
        )

        st.markdown("**Was efficiency measured?**")
        profile_path = PROJECT / "outputs/performance_profile_summary.csv"
        if profile_path.exists():
            profile = pd.read_csv(profile_path)
            pair = profile[profile["instance_id"].eq(selected_id)].copy()
        else:
            pair = pd.DataFrame()

        if not pair.empty:
            st.write(
                "Yes — this example was included in the paired performance "
                "study. Each query had one warm-up and three measured runs."
            )
            display_columns = [
                "query_kind",
                "repetitions",
                "db_hits_median",
                "client_elapsed_profile_ms_median",
            ]
            st.dataframe(
                pair[display_columns].rename(
                    columns={
                        "query_kind": "Query",
                        "repetitions": "Measured runs",
                        "db_hits_median": "Median database hits",
                        "client_elapsed_profile_ms_median": "Median client time with PROFILE (ms)",
                    }
                ),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "Database hits describe work recorded by plan operators. "
                "Client timing includes network transfer and PROFILE overhead. "
                "These measurements apply to the tested graph and session."
            )
        else:
            plan_status = text(row.get("performance_status"))
            if plan_status == "source_graph_unavailable":
                st.write(
                    "Performance was not assessed because the source "
                    "database was unavailable."
                )
            elif plan_status == "generated_syntax_error":
                st.write(
                    "Performance was not assessed because the generated "
                    "query contains a syntax error."
                )
            elif plan_status == "plan_inspected_no_cartesian_product":
                st.write(
                    "This example was outside the measured subset. "
                    "Its query plan was inspected; the saved evidence "
                    "is available below."
                )
            else:
                st.write(
                    "This example was outside the measured subset. "
                    "See the technical evidence for its plan-check status."
                )

    st.caption("STEP 4 · THE SAVED REVIEW")
    show_saved_review(row)

    review = text(row.get("logical_review_category"))
    if review:
        with st.expander("Earlier automatic review category"):
            st.markdown("**" + readable(review, REVIEW) + "**")
            st.write(text(row.get("logical_review_notes")))
            st.caption(
                "This preliminary category is preserved separately "
                "from the saved review decision."
            )

    with st.expander("See saved answer samples"):
        st.write(
            "These previews contain a few saved rows, sometimes shortened. "
            "They are not the complete answers and are not a fresh database run."
        )
        left, right = st.columns(2)
        with left:
            st.markdown("**Reference answer sample**")
            st.code(
                text(row.get("logical_reference_preview")) or "(No preview recorded)",
                language="text",
            )
        with right:
            st.markdown("**Generated answer sample**")
            st.code(
                text(row.get("logical_generated_preview")) or "(No preview recorded)",
                language="text",
            )

    st.subheader("How similar is the query text?")
    metrics = st.columns(2)
    score = pd.to_numeric(row.get("bleu_score"), errors="coerce")
    metrics[0].metric(
        "BLEU text similarity",
        f"{score:.1f} / 100" if pd.notna(score) else "Unavailable",
    )
    match = text(row.get("case_sensitive_trimmed_exact_match"))
    metrics[1].metric(
        "Exact text match",
        (
            "Yes"
            if match in {"1", "1.0"}
            else ("No" if match in {"0", "0.0"} else "Unavailable")
        ),
    )
    st.caption(
        "BLEU measures text overlap. Exact Match here compares trimmed "
        "text with case preserved. Neither measures answer correctness."
    )

    with st.expander("Understand the graph description"):
        st.write(
            "A graph stores entities as nodes, links as relationships "
            "and details as properties. The schema describes these names."
        )
        st.code(text(row["schema"]), language="text")

    with st.expander("View technical evidence"):
        for title, prefix in [
            ("Syntax validation", "syntax_"),
            ("Schema checks", "schema_"),
            ("Database result comparison", "logical_"),
            ("Query-plan inspection", "performance_"),
            ("Saved review decision", "manual_"),
        ]:
            st.markdown("**" + title + "**")
            evidence(row, prefix)

    st.download_button(
        "Download this example and its evidence",
        filtered[filtered["instance_id"] == selected_id]
        .to_csv(index=False)
        .encode("utf-8"),
        file_name=f"{selected_id}.csv",
        mime="text/csv",
    )

elif page == "Model comparison":
    from benchmark_view import show_benchmark

    show_benchmark(PROJECT)

else:
    st.subheader("Results across the research sample")
    columns = st.columns(4)
    values = [
        ("Questions in the sample", len(data)),
        ("With source database aliases", summary["records_with_source_graph_alias"]),
        (
            "Confirmed syntax errors",
            summary["generated_syntax_status"].get("syntax_error", 0),
        ),
        (
            "Observed result matches",
            summary["logical_status"].get("observed_result_match", 0),
        ),
    ]
    for column, (label, value) in zip(columns, values):
        column.metric(label, value)

    st.caption(
        "Database aliases describe potential evaluation coverage. "
        "Some comparisons remain inconclusive or require review."
    )

    st.subheader("What happened when answers were compared?")
    horizontal_chart(data["logical_status"], lambda value: outcome(value)[0])

    st.subheader("What did the review of flagged cases find?")
    reviewed = data[data["manual_logical_review_status"] != "not_reviewed"]

    columns = st.columns(4)
    columns[0].metric("Flagged cases reviewed", len(reviewed))
    columns[1].metric(
        "Errors identified under review rules",
        int(
            reviewed["manual_logical_review_status"]
            .eq("confirmed_generated_error_under_recorded_rules")
            .sum()
        ),
    )
    columns[2].metric(
        "Acceptable output alternatives",
        int(
            reviewed["manual_logical_review_status"]
            .eq("acceptable_output_alternative")
            .sum()
        ),
    )
    columns[3].metric(
        "Without a final binary label",
        int(
            reviewed["manual_logical_review_status"]
            .eq("reviewed_without_final_binary_label")
            .sum()
        ),
    )

    st.write(
        "The review examined cases where the automatic comparison found "
        "different values or different output formats. A different output "
        "can be a genuine query error, an acceptable way to answer, or a "
        "case where the question or reference is unclear."
    )
    st.caption(
        "These counts describe the reviewed subset. They are not an overall "
        "error rate across all 200 questions. Uncertain cases are not counted "
        "as correct. The reviews were AI-assisted and have not been "
        "independently adjudicated."
    )

    horizontal_chart(
        reviewed["manual_logical_review_status"],
        lambda value: readable(value, MANUAL_REVIEW_LABELS),
    )

    st.button(
        "Explore the reviewed cases",
        on_click=navigate,
        args=("Explore an example",),
    )

    st.subheader("What did query-plan inspection find?")
    horizontal_chart(
        data["performance_status"],
        lambda value: readable(value, PERFORMANCE),
    )
    st.caption("A plan without a Cartesian product is not automatically efficient.")

    st.subheader("How do these results answer the research questions?")
    st.markdown(
        "**RQ1 — What kinds of failures occur?** "
        "The syntax checks, schema checks and reviewed query differences "
        "describe the failure patterns found, while keeping uncertain "
        "and unavailable cases visible."
    )
    st.markdown(
        "**RQ2 — Do text scores reflect query problems?** "
        "BLEU and Exact Match are compared with recorded syntax outcomes "
        "and determinate logical-review assessments. These are descriptive "
        "associations within the stated samples."
    )

    st.subheader("Review across all three sample groups")
    validation_path = PROJECT / "outputs/human_validation.csv"
    if validation_path.exists():
        validation = pd.read_csv(validation_path)
        st.write(
            "The 40-case review covers 10 short, 20 medium-length and "
            "10 long questions. These groups describe question length."
        )
        assessments = {
            "syntax_assessment": "Syntax",
            "schema_assessment": "Schema",
            "logical_assessment": "Query meaning",
            "reference_assessment": "Reference quality",
        }
        review_counts = []
        for field, label in assessments.items():
            if field in validation.columns:
                for assessment, count in validation[field].value_counts().items():
                    review_counts.append(
                        {
                            "Check": label,
                            "Assessment": str(assessment).replace("_", " "),
                            "Cases": int(count),
                        }
                    )
        st.dataframe(
            pd.DataFrame(review_counts),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Student-verified, AI-assisted assessments; not an independent "
            "accuracy estimate. Uncertain cases remain separate."
        )
    else:
        st.info("The saved 40-case review file is unavailable.")

    st.subheader("Measured performance")
    profile_path = PROJECT / "outputs/performance_profile_summary.csv"
    if profile_path.exists():
        profile = pd.read_csv(profile_path)
        st.metric("Measured query pairs", profile["instance_id"].nunique())
        st.write(
            f"Generated and reference queries were measured for {profile['instance_id'].nunique()} "
            "previously matching pairs. Warm-ups are excluded from the "
            "summary; each query has three measured repetitions."
        )
        st.caption(
            "This selected subset does not establish efficiency across "
            "all 200 queries. Timing includes network transfer and PROFILE overhead."
        )
        with st.expander("View performance measurements"):
            st.dataframe(profile, hide_index=True, width="stretch")
        st.download_button(
            "Download performance measurements",
            profile_path.read_bytes(),
            file_name=profile_path.name,
            mime="text/csv",
        )

    correlation_path = PROJECT / "outputs/spearman_results.csv"
    if correlation_path.exists():
        st.subheader("Text scores and recorded error assessments")
        correlations = pd.read_csv(correlation_path)
        display = correlations[
            ["metric", "target", "paired_records", "spearman_rho"]
        ].copy()

        display["metric"] = display["metric"].replace(
            {
                "bleu_score": "BLEU",
                "exact_match": "Exact Match — historical",
                "case_sensitive_trimmed_exact_match": "Exact Match — case-sensitive",
            }
        )
        display["target"] = display["target"].replace(
            {
                "neo4j_syntax_error": "Syntax checks",
                "validation_review_logical_error": "40-case review: determinate cases",
                "reviewed_error_vs_acceptable_alternative": "Flagged review: errors vs alternatives",
            }
        )
        display["spearman_rho"] = display["spearman_rho"].map(
            lambda value: (f"{value:.3f}" if pd.notna(value) else "Not defined")
        )
        display = display.rename(
            columns={
                "metric": "Text metric",
                "target": "Compared with",
                "paired_records": "Cases",
                "spearman_rho": "Correlation",
            }
        )
        st.dataframe(display, hide_index=True, width="stretch")

        with st.expander("View the full correlation evidence"):
            st.dataframe(correlations, hide_index=True, width="stretch")
        st.caption(
            "Negative correlations mean higher text scores tended to accompany "
            "the no-error category under the recorded rules. The sample and "
            "review method limit interpretation. A blank coefficient means "
            "the correlation could not be calculated."
        )

    st.subheader("Research figures")
    figure_folder = PROJECT / "outputs/final_figures"
    figures = [
        ("figure_01_evaluation_coverage", "Evaluation outcomes and coverage"),
        ("figure_02_bleu_by_question_length", "BLEU by question length"),
        ("figure_03_bleu_by_review_outcome", "BLEU by flagged-case review outcome"),
        ("figure_04_validation_assessments", "The 40-case review"),
        ("figure_05_paired_performance", "Paired performance measurements"),
    ]
    caption_path = figure_folder / "figure_captions.csv"
    with st.expander("View and download the final figures"):
        for filename, title in figures:
            png = figure_folder / (filename + ".png")
            pdf = figure_folder / (filename + ".pdf")
            if png.exists():
                st.markdown("**" + title + "**")
                st.image(str(png), width="stretch")
                if pdf.exists():
                    st.download_button(
                        "Download PDF",
                        pdf.read_bytes(),
                        file_name=pdf.name,
                        mime="application/pdf",
                        key="download_" + filename,
                    )
        if caption_path.exists():
            st.markdown("**Figure captions and interpretation**")
            st.dataframe(
                pd.read_csv(caption_path),
                hide_index=True,
                width="stretch",
            )

    st.subheader("Download the evidence")
    left, right = st.columns(2)
    left.download_button(
        "Download all evaluation records",
        data.to_csv(index=False).encode("utf-8"),
        file_name="evaluation_results.csv",
        mime="text/csv",
        width="stretch",
    )
    right.download_button(
        "Download the evaluation summary",
        SUMMARY.read_bytes(),
        file_name="evaluation_summary.json",
        mime="application/json",
        width="stretch",
    )

    with st.expander("How to interpret these results"):
        st.write(
            "All 48 flagged comparison cases have first-pass review notes. "
            "Some remain uncertain because the question, reference or "
            "available evidence does not support a reliable binary decision. "
            "Schema checks are preliminary, and query-plan inspection "
            "does not measure execution speed."
        )
        for limitation in summary["limitations"]:
            st.write("• " + limitation)

    with st.expander("Research provenance and historical labels"):
        st.json(
            {
                "assembled_at_utc": summary["assembled_at_utc"],
                "input_sha256": summary["input_sha256"],
                "diagnostic_sha256": summary["diagnostic_sha256"],
                "manual_logical_review": summary.get("manual_logical_review", {}),
            }
        )
        st.caption(
            "Historical classifier labels remain in the downloaded table "
            "with a legacy_ prefix; they are not validated final counts."
        )

st.divider()
st.caption(
    "Shreya Nair · Honours research · "
    "Original generated and reference queries are preserved."
)
