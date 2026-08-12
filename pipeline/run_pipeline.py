"""
run_pipeline.py
Phase 4 — Full Pipeline Runner
Robustness Testing for LLM-Based Text-to-Cypher Systems

Runs all four classifiers in sequence and produces a
complete error classification summary across all 200 queries.

Order of execution:
1. Syntax classifier
2. Schema hallucination classifier
3. Logical classifier
4. Performance classifier

"""

import pandas as pd
from syntax_classifier import run_syntax_classifier
from schema_classifier import run_schema_classifier
from logical_classifier import run_logical_classifier
from performance_classifier import run_performance_classifier

# ─────────────────────────────────────────
# RUN ALL CLASSIFIERS
# ─────────────────────────────────────────

def run_full_pipeline():
    print("\n" + "="*60)
    print("FULL ERROR CLASSIFICATION PIPELINE")
    print("Robustness Testing for LLM-Based Text-to-Cypher Systems")
    print("="*60 + "\n")

    print("Step 1/4 — Syntax Classifier")
    run_syntax_classifier()

    print("\nStep 2/4 — Schema Hallucination Classifier")
    run_schema_classifier()

    print("\nStep 3/4 — Logical Error Classifier")
    run_logical_classifier()

    print("\nStep 4/4 — Performance Classifier")
    run_performance_classifier()

    # ─────────────────────────────────────────
    # FINAL SUMMARY
    # ─────────────────────────────────────────

    print("\n" + "="*60)
    print("PIPELINE COMPLETE — FINAL SUMMARY")
    print("="*60)

    df = pd.read_csv("data/generated_queries.csv")
    total = len(df)

    syntax      = df['syntax_error'].sum() if 'syntax_error' in df.columns else 0
    schema      = df['schema_hallucination'].sum() if 'schema_hallucination' in df.columns else 0
    logical     = df['logical_error'].sum() if 'logical_error' in df.columns else 0
    performance = df['performance_error'].sum() if 'performance_error' in df.columns else 0

    # Queries with any error
    any_error = df[
        (df.get('syntax_error', 0) == 1) |
        (df.get('schema_hallucination', 0) == 1) |
        (df.get('logical_error', 0) == 1) |
        (df.get('performance_error', 0) == 1)
    ].shape[0]

    print(f"\n{'Error Type':<30} {'Count':>8} {'Percentage':>12}")
    print("-"*52)
    print(f"{'Syntax errors':<30} {syntax:>8} {syntax/total*100:>11.1f}%")
    print(f"{'Schema hallucinations':<30} {schema:>8} {schema/total*100:>11.1f}%")
    print(f"{'Logical errors':<30} {logical:>8} {logical/total*100:>11.1f}%")
    print(f"{'Performance issues':<30} {performance:>8} {performance/total*100:>11.1f}%")
    print("-"*52)
    print(f"{'Queries with any error':<30} {any_error:>8} {any_error/total*100:>11.1f}%")
    print(f"{'Fully correct queries':<30} {total-any_error:>8} {(total-any_error)/total*100:>11.1f}%")
    print(f"\nTotal queries analysed: {total}")
    print("="*60)


if __name__ == "__main__":
    run_full_pipeline()