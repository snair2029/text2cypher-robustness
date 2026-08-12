"""
cross_tabulation.py
Phase 5 — Cross-Tabulation Analysis
Robustness Testing for LLM-Based Text-to-Cypher Systems

Produces cross-tabulation of error types against query complexity
levels (simple, medium, complex) to identify whether certain error
types are more prevalent at specific complexity levels.
Addresses RQ1: what are the most common failure modes.

"""

import pandas as pd
import os

# ─────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────

def load_data():
    df = pd.read_csv("data/generated_queries.csv")
    df['complexity'] = df['complexity'].fillna('unknown').astype(str)
    df['syntax_error'] = df['syntax_error'].fillna(0).astype(int)
    df['schema_hallucination'] = df['schema_hallucination'].fillna(0).astype(int)
    df['logical_error'] = df['logical_error'].fillna(0).astype(int)
    df['performance_error'] = df['performance_error'].fillna(0).astype(int)
    df['bleu_score'] = df['bleu_score'].fillna(0).astype(float)
    df['exact_match'] = df['exact_match'].fillna(0).astype(int)
    return df


# ─────────────────────────────────────────
# CROSS-TABULATION
# ─────────────────────────────────────────

def run_cross_tabulation():
    df = load_data()
    complexity_order = ['simple', 'medium', 'complex']

    print("Cross-Tabulation Analysis")
    print("="*60)

    # ── Error counts by complexity ──
    print("\nError Type Distribution by Complexity Level")
    print("-"*60)

    error_cols = {
        'Syntax Error': 'syntax_error',
        'Schema Hallucination': 'schema_hallucination',
        'Logical Error': 'logical_error',
        'Performance Issue': 'performance_error'
    }

    results = []
    print(f"\n{'Error Type':<25} {'Simple':>8} {'Medium':>8} "
          f"{'Complex':>8} {'Total':>8}")
    print("-"*60)

    for label, col in error_cols.items():
        row = {'Error Type': label}
        total = 0
        counts = []
        for c in complexity_order:
            count = df[df['complexity'] == c][col].sum()
            row[c] = int(count)
            counts.append(int(count))
            total += count
        row['Total'] = int(total)
        results.append(row)
        print(f"{label:<25} {counts[0]:>8} {counts[1]:>8} "
              f"{counts[2]:>8} {total:>8}")

    # Any error row
    df['any_error'] = (
        (df['syntax_error'] == 1) |
        (df['schema_hallucination'] == 1) |
        (df['logical_error'] == 1) |
        (df['performance_error'] == 1)
    ).astype(int)

    print("-"*60)
    any_counts = []
    any_total = 0
    for c in complexity_order:
        count = df[df['complexity'] == c]['any_error'].sum()
        any_counts.append(int(count))
        any_total += count
    print(f"{'Any Error':<25} {any_counts[0]:>8} {any_counts[1]:>8} "
          f"{any_counts[2]:>8} {any_total:>8}")

    # ── Queries per complexity ──
    print(f"\n{'Total Queries':<25} ", end="")
    for c in complexity_order:
        print(f"{len(df[df['complexity']==c]):>8}", end="")
    print(f"{len(df):>8}")

    # ── Error rate by complexity ──
    print("\n\nError Rate by Complexity Level (percentage)")
    print("-"*60)
    print(f"\n{'Error Type':<25} {'Simple':>8} {'Medium':>8} {'Complex':>8}")
    print("-"*50)

    n_simple = len(df[df['complexity'] == 'simple'])
    n_medium = len(df[df['complexity'] == 'medium'])
    n_complex = len(df[df['complexity'] == 'complex'])

    for label, col in error_cols.items():
        s = df[df['complexity']=='simple'][col].sum() / n_simple * 100
        m = df[df['complexity']=='medium'][col].sum() / n_medium * 100
        c = df[df['complexity']=='complex'][col].sum() / n_complex * 100
        print(f"{label:<25} {s:>7.1f}% {m:>7.1f}% {c:>7.1f}%")

    # ── BLEU by complexity ──
    print("\n\nAverage BLEU Score by Complexity Level")
    print("-"*60)
    bleu_by_complexity = df.groupby('complexity')['bleu_score'].agg(
        ['mean', 'median', 'std']
    ).reindex(complexity_order)
    print(bleu_by_complexity.round(2).to_string())

    # ── Save results ──
    results_df = pd.DataFrame(results)
    results_df.to_csv("outputs/cross_tabulation.csv", index=False)

    bleu_by_complexity.round(2).to_csv("outputs/bleu_by_complexity.csv")

    print("\n" + "="*60)
    print("Saved → outputs/cross_tabulation.csv")
    print("Saved → outputs/bleu_by_complexity.csv")
    print("="*60)


if __name__ == "__main__":
    os.makedirs("outputs", exist_ok=True)
    run_cross_tabulation()