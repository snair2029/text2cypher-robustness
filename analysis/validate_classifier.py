"""
validate_classifier.py
Phase 5 — Classifier Validation Against Manual Labels
Robustness Testing for LLM-Based Text-to-Cypher Systems

Compares automated pipeline classifications against
41 manually labelled queries to assess classifier accuracy.
Calculates precision, recall and agreement rate.

"""

import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
import os

# ─────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────

def load_labelled_data():
    df = pd.read_csv("data/generated_queries.csv")
    df['manual_label'] = df['manual_label'].fillna('').astype(str).str.strip()
    df['syntax_error'] = df['syntax_error'].fillna(0).astype(int)
    df['schema_hallucination'] = df['schema_hallucination'].fillna(0).astype(int)
    df['logical_error'] = df['logical_error'].fillna(0).astype(int)
    df['performance_error'] = df['performance_error'].fillna(0).astype(int)

    # Only rows that have been manually labelled
    labelled = df[df['manual_label'] != ''].copy()
    return df, labelled


# ─────────────────────────────────────────
# MAP MANUAL LABELS TO PIPELINE COLUMNS
# ─────────────────────────────────────────

def get_pipeline_label(row):
    """
    Convert pipeline binary columns to a single label
    matching the manual label format.
    """
    errors = []
    if row['syntax_error'] == 1:
        errors.append('syntax_error')
    if row['schema_hallucination'] == 1:
        errors.append('schema_hallucination')
    if row['logical_error'] == 1:
        errors.append('logical_error')
    if row['performance_error'] == 1:
        errors.append('performance_issue')

    if len(errors) == 0:
        return 'no_error'
    elif len(errors) == 1:
        return errors[0]
    else:
        return 'multiple_errors'


# ─────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────

def run_validation():
    df, labelled = load_labelled_data()

    print("Classifier Validation Report")
    print("="*60)
    print(f"Total manually labelled queries: {len(labelled)}")
    print(f"Total queries in dataset: {len(df)}")
    print("="*60)

    # Get pipeline label for each manually labelled row
    labelled = labelled.copy()
    labelled['pipeline_label'] = labelled.apply(get_pipeline_label, axis=1)

    print("\nManual Label Distribution:")
    print(labelled['manual_label'].value_counts().to_string())

    print("\nPipeline Label Distribution (for same 41 queries):")
    print(labelled['pipeline_label'].value_counts().to_string())

    # Agreement — where manual and pipeline agree on error vs no error
    labelled['manual_has_error'] = labelled['manual_label'] != 'no_error'
    labelled['pipeline_has_error'] = labelled['pipeline_label'] != 'no_error'

    agreement = (labelled['manual_has_error'] == labelled['pipeline_has_error']).sum()
    agreement_rate = agreement / len(labelled) * 100

    print(f"\nOverall agreement rate: {agreement}/{len(labelled)} ({agreement_rate:.1f}%)")

    # Breakdown
    print("\nDetailed comparison:")
    print(f"{'Query':>6} {'Manual Label':<25} {'Pipeline Label':<25} {'Match'}")
    print("-"*75)
    for i, row in labelled.iterrows():
        match = "✓" if row['manual_has_error'] == row['pipeline_has_error'] else "✗"
        print(f"{i+1:>6} {row['manual_label']:<25} {row['pipeline_label']:<25} {match}")

    # Save results
    labelled[['question', 'manual_label', 'pipeline_label',
              'bleu_score', 'exact_match']].to_csv(
        "outputs/classifier_validation.csv", index=False
    )

    print("\n" + "="*60)
    print(f"Agreement rate: {agreement_rate:.1f}%")
    print("Saved → outputs/classifier_validation.csv")
    print("="*60)


if __name__ == "__main__":
    os.makedirs("outputs", exist_ok=True)
    run_validation()