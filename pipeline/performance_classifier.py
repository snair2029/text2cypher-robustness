"""
performance_classifier.py
Phase 4 — Performance Issue Classifier
Robustness Testing for LLM-Based Text-to-Cypher Systems

Detects generated Cypher queries that are functionally correct
but structurally inefficient. Uses Neo4j EXPLAIN to analyse
the query execution plan and flags queries with known
performance anti-patterns such as Cartesian products and
missing index usage.

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


def check_performance(session, query):
    """
    Run EXPLAIN on the query and check for performance anti-patterns.
    Returns (has_issue: bool, detail: str)
    """
    try:
        explain_query = f"EXPLAIN {query}"
        result = session.run(explain_query)
        summary = result.consume()
        plan = summary.plan

        issues = []

        if plan:
            plan_str = str(plan)

            # Check for Cartesian product — inefficient cross joins
            if 'CartesianProduct' in plan_str:
                issues.append("Cartesian product detected")

            # Check for full node scans without index
            if 'AllNodesScan' in plan_str:
                issues.append("Full node scan — no index used")

            # Check for NodeByLabelScan without property filter
            if 'NodeByLabelScan' in plan_str and 'Filter' not in plan_str:
                issues.append("Label scan without property filter")

        if issues:
            return True, "; ".join(issues)
        return False, ""

    except Exception as e:
        return False, ""


# ─────────────────────────────────────────
# MAIN CLASSIFIER
# ─────────────────────────────────────────

def run_performance_classifier():
    df = pd.read_csv("data/generated_queries.csv")
    df['generated_cypher'] = df['generated_cypher'].fillna('').astype(str)
    df['syntax_error'] = df['syntax_error'].fillna(0).astype(int)

    if 'performance_error' not in df.columns:
        df['performance_error'] = 0
    if 'performance_error_msg' not in df.columns:
        df['performance_error_msg'] = ''

    df['performance_error'] = df['performance_error'].fillna(0).astype(int)
    df['performance_error_msg'] = df['performance_error_msg'].fillna('').astype(str)

    print("Performance Issue Classifier")
    print("="*50)
    print("Connecting to Neo4j AuraDB...")

    driver = get_driver()
    driver.verify_connectivity()
    print("Connected.")
    print("="*50)

    performance_count = 0
    skipped = 0

    with driver.session() as session:
        for i, row in df.iterrows():
            query = row['generated_cypher']

            if not query or query.strip() == '':
                skipped += 1
                continue

            # Skip queries already flagged as syntax errors
            if row['syntax_error'] == 1:
                df.at[i, 'performance_error'] = 0
                df.at[i, 'performance_error_msg'] = 'Skipped — syntax error'
                continue

            has_issue, msg = check_performance(session, query)

            df.at[i, 'performance_error'] = 1 if has_issue else 0
            df.at[i, 'performance_error_msg'] = msg if has_issue else ''

            if has_issue:
                performance_count += 1
                print(f"[{i+1}] PERFORMANCE | {msg}")
                print(f"      {row['question'][:70]}")

            # Save every 20 rows
            if (i + 1) % 20 == 0:
                df.to_csv("data/generated_queries.csv", index=False)
                print(f"--- Saved at row {i+1} ---")

    driver.close()
    df.to_csv("data/generated_queries.csv", index=False)

    print("="*50)
    print(f"Performance issues : {performance_count} / 200")
    print(f"Efficient queries  : {200 - performance_count - skipped} / 200")
    print(f"Skipped            : {skipped} / 200")
    print("Saved → data/generated_queries.csv")


if __name__ == "__main__":
    run_performance_classifier()