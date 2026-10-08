"""Saved model comparison interface; does not execute queries."""
from pathlib import Path
import pandas as pd
import streamlit as st


def show_benchmark(project: Path):
    folder=project/'outputs/benchmark_comparison'
    required=['model_metrics.csv','logical_outcome_counts.csv','paired_logical_outcomes.csv','paired_match_counts.csv']
    if any(not (folder/name).exists() for name in required):
        st.warning('Build the saved benchmark comparison first.')
        st.code('python scripts/build_model_metrics.py\npython scripts/build_benchmark_comparison.py')
        return
    metrics=pd.read_csv(folder/'model_metrics.csv',keep_default_na=False)
    counts=pd.read_csv(folder/'logical_outcome_counts.csv',keep_default_na=False)
    pairs=pd.read_csv(folder/'paired_logical_outcomes.csv',keep_default_na=False)
    st.header('Gemini versus Gemma')
    st.write('The same 200 questions, supplied schemas and reference queries were used for both models.')
    st.caption('Gemini 3.1 Flash Lite is recorded in the journal and generation script; per-query model metadata was not retained. Gemma records gemma-4-26b-a4b-it. Provider generation defaults were not explicitly controlled, so this is a comparison of the recorded runs.')
    for col,(_,row) in zip(st.columns(2),metrics.iterrows()):
        with col:
            st.subheader(row['model'])
            st.metric('Mean sentence BLEU',f"{row['mean_sentence_bleu']:.4f}")
            st.metric('Trimmed Exact Match',f"{int(row['case_sensitive_trimmed_exact_match_count'])}/200")
            st.metric('Neo4j syntax accepted',f"{int(row['syntax_accepted_count'])}/200")
    st.caption('BLEU averages saved sentence scores over all 200 queries, including zeros. Exact Match is case-sensitive after trimming. Lowercase Exact Match is 14/200 for each model. Text similarity and syntax acceptance do not establish query correctness.')
    st.subheader('Database evaluation outcomes')
    st.dataframe(counts.rename(columns={'logical_status':'Saved outcome'}),hide_index=True,use_container_width=True)
    st.image(str(folder/'logical_outcomes.png'))
    st.info('Each model has 89 source-graph-unavailable outcomes, but only 88 are the same questions. Syntax failures can be recorded before graph checks. Unavailable and inconclusive cases are retained, and public graphs were not immutable snapshots.')
    st.subheader('Paired reference-result agreement')
    st.image(str(folder/'paired_matches.png'))
    st.caption('An observed match means agreement with the reference on the tested graph. “Neither observed match” includes unavailable, review and inconclusive cases; it is not a count of incorrect answers.')
    st.subheader('Inspect the same question')
    gemini=pd.read_csv(project/'data/generated_queries.csv',keep_default_na=False).set_index('instance_id')
    gemma=pd.read_csv(project/'outputs/benchmark_gemma_26b.csv',keep_default_na=False).set_index('instance_id')
    selected=st.selectbox('Question ID',pairs.instance_id.tolist(),key='benchmark_question')
    st.write(gemini.loc[selected,'question'])
    with st.expander('Supplied schema'):st.code(gemini.loc[selected,'schema'])
    st.code(gemini.loc[selected,'cypher'],language='cypher')
    st.caption('Dataset reference query')
    evidence=pairs.set_index('instance_id').loc[selected]
    for col,name,df,suffix in zip(st.columns(2),['Gemini','Gemma'],[gemini,gemma],['gemini','gemma']):
        with col:
            st.subheader(name)
            st.code(df.loc[selected,'generated_cypher'],language='cypher')
            st.write('Saved outcome: '+evidence['logical_status_'+suffix].replace('_',' '))
            with st.expander('Saved execution evidence'):
                for key in ['generated_row_count','reference_row_count','generated_error','reference_error','generated_preview','reference_preview']:
                    st.write(key.replace('_',' ').capitalize()+':')
                    st.text(str(evidence.get(key+'_'+suffix,'')))
    review_path=project/'outputs/gemma_26b_logical_review.csv'
    if review_path.exists():
        reviews=pd.read_csv(review_path,keep_default_na=False)
        st.subheader('Gemma flagged-case review')
        st.caption('AI-assisted inspection of 47 flagged cases using queries, supplied schemas and saved previews. No independent adjudication or database rerun; these are not an overall correctness rate.')
        st.dataframe(reviews.final_review_decision.value_counts().rename_axis('Decision').reset_index(name='Cases'),hide_index=True)
        chosen=reviews[reviews.instance_id.eq(selected)]
        if not chosen.empty:
            st.write('Review: '+chosen.iloc[0].final_review_decision.replace('_',' '))
            st.write(chosen.iloc[0].review_reason)
    review_counts_path=folder/'verified_40_review_counts.csv'
    if review_counts_path.exists():
        st.subheader('Same 40-question review sample')
        st.caption('The same question IDs and order were inspected for both models. Student verification is recorded; source assistance disclosures remain. Uncertain decisions are retained. This selected sample is not independent ground truth or overall accuracy.')
        st.dataframe(pd.read_csv(review_counts_path),hide_index=True,use_container_width=True)
        st.image(str(folder/'verified_40_logical_reviews.png'))
    performance_path=folder/'performance_comparison_summary.csv'
    if performance_path.exists():
        st.subheader('Saved query performance')
        performance=pd.read_csv(performance_path)
        st.dataframe(performance.rename(columns={'model':'Model','common_cases':'Common questions','median_db_hits':'Median database hits','median_recorded_client_profile_ms':'Median recorded client PROFILE time (ms)'}),hide_index=True,use_container_width=True)
        st.caption('Only common questions with three measured repetitions and nonempty reference agreement are included. Warm-ups are excluded. Runs occurred at different times; client timing includes network transfer and PROFILE overhead. This does not measure model generation speed or establish a controlled latency difference.')
        figure=folder/'performance_comparison.png'
        if figure.exists():st.image(str(figure))
        with st.expander('Paired performance measurements'):
            paired_path=folder/'paired_performance_measurements.csv'
            if paired_path.exists():
                st.dataframe(pd.read_csv(paired_path),hide_index=True,use_container_width=True)
                st.download_button('Download paired performance records',paired_path.read_bytes(),file_name=paired_path.name,mime='text/csv',key='download_performance_pairs')
    st.subheader('Download comparison evidence')
    for name in ['model_metrics.csv','logical_outcome_counts.csv','paired_match_counts.csv','paired_outcome_crosstab.csv','paired_logical_outcomes.csv']:
        st.download_button(name,(folder/name).read_bytes(),file_name=name,mime='text/csv',key='download_'+name)
