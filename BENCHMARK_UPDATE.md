# Apply and check the benchmark extension

Extract this update ZIP into the existing text2cypher_research project root. It contains updated app.py and README.md, a new benchmark_view.py, two build scripts, comparison outputs and separate schema review notes. Original generation CSVs, existing evaluators and original Gemini review files are not replaced.

With the text2cypher environment active:

    python scripts/build_model_metrics.py
    python scripts/build_benchmark_comparison.py
    streamlit run app.py

Open Model comparison in the sidebar. Check the two metric summaries and select a question to view both generated queries and saved evidence. No model requests or database execution are needed. Keep your existing Streamlit/SSH forwarding arrangement if launching remotely.

Expected metrics: Gemini BLEU 60.2673, trimmed case-sensitive EM 13/200, syntax accepted 198/200; Gemma BLEU 58.9396, EM 12/200, syntax accepted 183/200. Observed matches: Gemini 52, Gemma 38; both 34, Gemini only 18, Gemma only 4.

Validation completed: builders ran successfully against the supplied current project; all 200 question/schema/reference values align; IDs and source graph aliases align; outcome counts total 200 per model; changed Python files compile; comparison-page data access succeeds for every question using stubbed Streamlit calls. Actual Streamlit/browser rendering was not tested because Streamlit is unavailable in the editing workspace. BLEU scores were averaged from saved values, not regenerated with sacrebleu. The remaining live check is in your installed environment.

Journal screenshots: 06_Gemini_Gemma_Benchmark_Comparison.png and 07_Gemini_Gemma_Paired_Example.png. Three figure sets in outputs/benchmark_comparison are available in PNG and PDF for direct report inclusion.

These updates finish the comparison implementation and supporting documentation, not the final honours report. Review conclusions remain AI-assisted; unresolved cases and unavailable graphs are retained. Cross-model performance profiling has not been done and is not claimed.
