"""
logical_classifier.py
Phase 4 — Logical Error Classifier
Robustness Testing for LLM-Based Text-to-Cypher Systems

Detects queries that are syntactically valid and schema-conformant
but return different results from the reference query when executed
against a live Neo4j database.

Uses Neo4j AuraDB free tier for query execution.
Both the generated and reference queries are run against the same
empty database. If both return empty results they match — if one
fails to execute while the other succeeds, a logical error is flagged.

"""

import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

# ─────────────────────────────────────────
# NEO4J CONNECTION
# ─────────────────────────────────────────

URI      = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")


def get_driver():
    return GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


def run_query(session, query):
    """
    Execute a Cypher query and return (results, error).
    Results is a list of dicts. Error is a string if failed.
    """
    try:
        result = session.run(query)
        records = [dict(r) for r in result]
        return records, None
    except Exception as e:
        return None, str(e)[:300]


def compare_results(ref, gen):
    """
    Compare two result sets.
    Both empty = match. One fails = mismatch.
    """
    if ref is None or gen is None:
        return False
    try:
        ref_sorted = sorted([str(sorted(r.items())) for r in ref])
        gen_sorted = sorted([str(sorted(r.items())) for r in gen])
        return ref_sorted == gen_sorted
    except Exception:
        return False


# ─────────────────────────────────────────
# MAIN CLASSIFIER
# ─────────────────────────────────────────

def run_logical_classifier():
    df = pd.read_csv("data/generated_queries.csv")
    df['generated_cypher'] = df['generated_cypher'].fillna('').astype(str)
    df['cypher'] = df['cypher'].fillna('').astype(str)
    df['syntax_error'] = df['syntax_error'].fillna(0).astype(int)

    if 'logical_error' not in df.columns:
        df['logical_error'] = 0
    if 'logical_error_msg' not in df.columns:
        df['logical_error_msg'] = ''

    df['logical_error'] = df['logical_error'].fillna(0).astype(int)
    df['logical_error_msg'] = df['logical_error_msg'].fillna('').astype(str)

    print("Logical Error Classifier")
    print("="*50)
    print("Connecting to Neo4j AuraDB...")

    driver = get_driver()
    driver.verify_connectivity()
    print("Connected.")
    print("="*50)

    logical_count = 0
    skipped = 0

    with driver.session() as session:
        for i, row in df.iterrows():
            gen_query = row['generated_cypher']
            ref_query = row['cypher']

            # Skip empty queries
            if not gen_query or gen_query.strip() == '':
                skipped += 1
                continue

            # Skip queries already flagged as syntax errors
            if row['syntax_error'] == 1:
                df.at[i, 'logical_error'] = 0
                df.at[i, 'logical_error_msg'] = 'Skipped — syntax error'
                continue

            ref_results, ref_err = run_query(session, ref_query)
            gen_results, gen_err = run_query(session, gen_query)

            # If generated query fails to execute
            if gen_err:
                df.at[i, 'logical_error'] = 1
                df.at[i, 'logical_error_msg'] = f"Execution failed: {gen_err[:200]}"
                logical_count += 1
                print(f"[{i+1}] EXEC FAIL | {gen_err[:60]}")
                print(f"      {row['question'][:70]}")
                continue

            # Compare result sets
            is_match = compare_results(ref_results, gen_results)

            if not is_match:
                df.at[i, 'logical_error'] = 1
                df.at[i, 'logical_error_msg'] = "Result set differs from reference"
                logical_count += 1
                print(f"[{i+1}] LOGICAL ERROR | Results differ")
                print(f"      {row['question'][:70]}")
            else:
                df.at[i, 'logical_error'] = 0
                df.at[i, 'logical_error_msg'] = ''

            # Save every 20 rows
            if (i + 1) % 20 == 0:
                df.to_csv("data/generated_queries.csv", index=False)
                print(f"--- Saved at row {i+1} ---")

    driver.close()
    df.to_csv("data/generated_queries.csv", index=False)

    print("="*50)
    print(f"Logical errors   : {logical_count} / 200")
    print(f"Correct results  : {200 - logical_count - skipped} / 200")
    print(f"Skipped          : {skipped} / 200")
    print("Saved → data/generated_queries.csv")


if __name__ == "__main__":
    run_logical_classifier()