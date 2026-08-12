"""
spearman_correlation.py
Phase 5 — Spearman Rank Correlation Analysis
Robustness Testing for LLM-Based Text-to-Cypher Systems

Computes Spearman rank correlation between standard evaluation
metrics (BLEU, Exact Match) and each error type classification.
Addresses RQ2: whether standard metrics reflect actual error patterns.

"""

import pandas as pd
from scipy import stats
import os

# ─────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────

def load_data():
    df = pd.read_csv("data/generated_queries.csv")
    df['bleu_score'] = df['bleu_score'].fillna(0).astype(float)
    df['exact_match'] = df['exact_match'].fillna(0).astype(int)
    df['syntax_error'] = df['syntax_error'].fillna(0).astype(int)
    df['schema_hallucination'] = df['schema_hallucination'].fillna(0).astype(int)
    df['logical_error'] = df['logical_error'].fillna(0).astype(int)
    df['performance_error'] = df['performance_error'].fillna(0).astype(int)
    return df


# ─────────────────────────────────────────
# SPEARMAN CORRELATION
# ─────────────────────────────────────────

def compute_correlations(df):
    metrics = ['bleu_score', 'exact_match']
    error_types = [
        'syntax_error',
        'schema_hallucination',
        'logical_error',
        'performance_error'
    ]

    results = []

    for metric in metrics:
        for error in error_types:
            corr, pvalue = stats.spearmanr(df[metric], df[error])
            significant = "Yes" if pvalue < 0.05 else "No"
            results.append({
                'Metric': metric,
                'Error Type': error,
                'Spearman r': round(corr, 4),
                'P-value': round(pvalue, 4),
                'Significant (p<0.05)': significant
            })

    return pd.DataFrame(results)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def run_spearman_correlation():
    df = load_data()

    print("Spearman Rank Correlation Analysis")
    print("="*60)
    print("Metric vs Error Type Correlations")
    print("="*60)

    results_df = compute_correlations(df)

    # Print formatted table
    print(f"\n{'Metric':<15} {'Error Type':<25} {'r':>8} {'p-value':>10} {'Sig?':>8}")
    print("-"*70)
    for _, row in results_df.iterrows():
        print(f"{row['Metric']:<15} {row['Error Type']:<25} "
              f"{row['Spearman r']:>8.4f} {row['P-value']:>10.4f} "
              f"{row['Significant (p<0.05)']:>8}")

    print("\n" + "="*60)
    print("Interpretation:")
    print("r close to -1 = high metric score = fewer errors")
    print("r close to 0  = metric has no correlation with errors")
    print("r close to +1 = high metric score = more errors")
    print("="*60)

    # Also compute overall any-error correlation
    df['any_error'] = (
        (df['syntax_error'] == 1) |
        (df['schema_hallucination'] == 1) |
        (df['logical_error'] == 1) |
        (df['performance_error'] == 1)
    ).astype(int)

    print("\nCorrelation with ANY error present:")
    print(f"\n{'Metric':<15} {'r':>8} {'p-value':>10} {'Sig?':>8}")
    print("-"*45)
    for metric in ['bleu_score', 'exact_match']:
        corr, pvalue = stats.spearmanr(df[metric], df['any_error'])
        sig = "Yes" if pvalue < 0.05 else "No"
        print(f"{metric:<15} {corr:>8.4f} {pvalue:>10.4f} {sig:>8}")

    # Save results
    results_df.to_csv("outputs/spearman_results.csv", index=False)
    print("\nSaved → outputs/spearman_results.csv")


if __name__ == "__main__":
    os.makedirs("outputs", exist_ok=True)
    run_spearman_correlation()