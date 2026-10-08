"""Validate saved Cypher queries using Neo4j EXPLAIN.

EXPLAIN checks parsing and planning without executing the query.
Passing this check does not establish schema or logical correctness.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase, Query
from neo4j.exceptions import Neo4jError


PROJECT = Path(__file__).resolve().parents[1]
INPUT = PROJECT / "outputs" / "benchmark_gemma_26b.csv"
OUTPUT = PROJECT / "outputs" / "gemma_26b_syntax_validation.csv"

load_dotenv(PROJECT / ".env")


def validate_query(session, query):
    """Keep rejected queries separate from failed evaluations."""
    if pd.isna(query) or not str(query).strip():
        return {
            "status": "missing_query",
            "error_code": "",
            "message": "No query available",
        }

    try:
        session.run(
            Query("EXPLAIN " + str(query).strip(), timeout=30)
        ).consume()

        return {
            "status": "accepted",
            "error_code": "",
            "message": "",
        }

    except Neo4jError as exc:
        code = exc.code or type(exc).__name__

        if code == "Neo.ClientError.Statement.SyntaxError":
            status = "syntax_error"
        elif code.startswith("Neo.ClientError.Statement."):
            status = "other_statement_error"
        else:
            status = "evaluation_failed"

        return {
            "status": status,
            "error_code": code,
            "message": str(exc)[:1000],
        }

    except Exception as exc:
        return {
            "status": "evaluation_failed",
            "error_code": type(exc).__name__,
            "message": str(exc)[:1000],
        }


def save_results(records):
    """Save atomically so an interrupted write does not corrupt results."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp")
    pd.DataFrame(records).to_csv(temporary, index=False)
    temporary.replace(OUTPUT)


def main():
    required = ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")
    missing = [name for name in required if not os.getenv(name)]

    if missing:
        raise SystemExit(
            "Missing configuration: " + ", ".join(missing)
        )

    df = pd.read_csv(INPUT)
    required_columns = {"instance_id", "question", "generated_cypher", "cypher"}

    if not required_columns.issubset(df.columns):
        raise SystemExit("Input CSV is missing required columns.")

    if df["instance_id"].isna().any() or df["instance_id"].duplicated().any():
        raise SystemExit("Each record must have a unique, nonempty instance_id.")

    records = []
    database = os.getenv("NEO4J_DATABASE")
    options = {"database": database} if database else {}

    with GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(
            os.environ["NEO4J_USERNAME"],
            os.environ["NEO4J_PASSWORD"],
        ),
        connection_timeout=15,
    ) as driver:
        driver.verify_connectivity()
        server = driver.get_server_info()

        with driver.session(**options) as session:
            for number, (_, row) in enumerate(df.iterrows(), start=1):
                generated = validate_query(session, row["generated_cypher"])
                reference = validate_query(session, row["cypher"])

                record = {
                    "instance_id": row["instance_id"],
                    "question": row["question"],
                    "neo4j_version": server.agent,
                    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                }

                for prefix, result in (
                    ("generated", generated),
                    ("reference", reference),
                ):
                    for field, value in result.items():
                        record[f"{prefix}_{field}"] = value

                records.append(record)
                save_results(records)

                print(
                    f"[{number}/{len(df)}] "
                    f"Generated: {generated['status']} | "
                    f"Reference: {reference['status']}"
                )

                if (
                    generated["status"] == "evaluation_failed"
                    or reference["status"] == "evaluation_failed"
                ):
                    print(
                        "\nStopped because an evaluation failed. "
                        "Completed checks have been saved."
                    )
                    break

    results = pd.DataFrame(records)

    print("\nGENERATED QUERY STATUS")
    print(results["generated_status"].value_counts().to_string())

    print("\nREFERENCE QUERY STATUS")
    print(results["reference_status"].value_counts().to_string())

    print(f"\nRecords checked: {len(records)}/{len(df)}")
    print(f"Results saved to: {OUTPUT}")
    print("Gemini and Gemma query files were not changed.")


if __name__ == "__main__":
    main()