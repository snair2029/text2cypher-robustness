"""
Compare saved queries on their populated source graphs.

Results describe agreement with the reference on the current graph.
Agreement is not proof that either query answers the question correctly.
Original generated_queries.csv is never modified.
"""

import json
import os
from pathlib import Path
import re
import ssl
from collections import Counter
from datetime import datetime, timezone

import pandas as pd
from neo4j import GraphDatabase, Query, READ_ACCESS, unit_of_work
from neo4j.graph import Node, Relationship, Path as GraphPath

PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT / "outputs/logical_validation.csv"
REMOTE_HOST = "demo.neo4jlabs.com"
PREFIX = "neo4jlabs_demo_db_"
ROW_LIMIT = 5000
TIMEOUT = 30


class TunnelTLSContext(ssl.SSLContext):
    def wrap_socket(self, *args, **kwargs):
        kwargs["server_hostname"] = REMOTE_HOST
        return super().wrap_socket(*args, **kwargs)


def get_driver(database):
    """Use direct access, or the optional IHPC reverse tunnel."""
    options = {
        "auth": (database, database),
        "connection_timeout": 10,
        "connection_acquisition_timeout": 15,
        "max_transaction_retry_time": 0,
    }
    port = os.getenv("NEO4J_DEMO_TUNNEL_PORT")

    if port:
        context = TunnelTLSContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_default_certs()
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        options.update(encrypted=True, ssl_context=context)
        uri = f"bolt://127.0.0.1:{int(port)}"
    else:
        uri = f"bolt+s://{REMOTE_HOST}:7687"

    return GraphDatabase.driver(uri, **options)


def canonical(value):
    """Preserve types, duplicates and graph identity within this graph."""
    if isinstance(value, Node):
        return (
            "node", value.element_id,
            tuple(sorted(value.labels)), canonical(dict(value)),
        )
    if isinstance(value, Relationship):
        return (
            "relationship", value.element_id, value.type,
            value.start_node.element_id,
            value.end_node.element_id,
            canonical(dict(value)),
        )
    if isinstance(value, GraphPath):
        return (
            "path",
            tuple(canonical(n) for n in value.nodes),
            tuple(canonical(r) for r in value.relationships),
        )
    if isinstance(value, dict):
        return (
            "map",
            tuple(sorted((k, canonical(v)) for k, v in value.items())),
        )
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(canonical(v) for v in value))
    if value is None:
        return ("null",)
    if isinstance(value, (str, bool, int, float)):
        return (type(value).__name__, repr(value))
    if hasattr(value, "iso_format"):
        return (type(value).__name__, value.iso_format())
    return (type(value).__name__, repr(value))


@unit_of_work(timeout=TIMEOUT)
def evaluate_query(tx, query):
    # EXPLAIN checks the statement before execution.
    plan = tx.run("EXPLAIN " + query).consume()
    if plan.query_type != "r":
        raise ValueError("Only statements classified as read-only are allowed.")

    result = tx.run(query)
    columns = list(result.keys())
    rows = []
    preview = []

    for record in result:
        if len(rows) >= ROW_LIMIT:
            raise ValueError(f"Result exceeds the {ROW_LIMIT}-row limit.")
        values = tuple(record.values())
        rows.append(tuple(canonical(value) for value in values))
        if len(preview) < 3:
            preview.append([repr(value)[:300] for value in values])

    result.consume()
    return columns, rows, preview


def run_query(session, query):
    try:
        return session.execute_read(evaluate_query, query), ""
    except Exception as error:
        code = getattr(error, "code", type(error).__name__)
        return None, f"{code}: {error}"[:1000]


def comparison_mode(reference, generated):
    # Conservative heuristic: nested ORDER BY can also trigger this.
    # Keep the mode visible so ordering-sensitive cases can be reviewed.
    ordered = any(
        re.search(r"\bORDER\s+BY\b", query, re.IGNORECASE)
        for query in (reference, generated)
    )
    return "ordered_rows" if ordered else "unordered_rows_with_duplicates"


def save_results(records):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp")
    pd.DataFrame(records).to_csv(temporary, index=False)
    temporary.replace(OUTPUT)


def run_logical_classifier():
    queries = pd.read_csv(PROJECT / "data/generated_queries.csv")
    if queries["instance_id"].duplicated().any():
        raise ValueError("Duplicate instance IDs in the input.")

    inventory = pd.read_csv(PROJECT / "outputs/schema_inventory.csv")
    if inventory["instance_id"].duplicated().any():
        raise ValueError("Duplicate instance IDs in the schema inventory.")
    inventory = inventory.set_index("instance_id")

    syntax = pd.read_csv(
        PROJECT / "outputs/neo4j_syntax_validation.csv"
    ).set_index("instance_id")

    drivers = {}
    graph_checks = {}
    records = []

    def check_graph(database):
        if database not in graph_checks:
            try:
                drivers[database] = get_driver(database)
                with drivers[database].session(
                    database=database,
                    default_access_mode=READ_ACCESS,
                ) as session:
                    result = session.run(
                        Query("MATCH (n) RETURN n LIMIT 1", timeout=TIMEOUT)
                    )
                    populated = result.single() is not None
                    summary = result.consume()
                    labels = {
                        record[0] for record in session.run(
                            Query("CALL db.labels()", timeout=TIMEOUT)
                        )
                    }
                    types = {
                        record[0] for record in session.run(
                            Query("CALL db.relationshipTypes()", timeout=TIMEOUT)
                        )
                    }
                    graph_checks[database] = (
                        populated, labels, types, summary.server.agent, ""
                    )
            except Exception as error:
                graph_checks[database] = (
                    False, set(), set(), "",
                    f"{type(error).__name__}: {error}"[:1000],
                )
        return graph_checks[database]

    print("Logical evaluation on source graphs", flush=True)

    try:
        for position, (_, row) in enumerate(queries.iterrows(), 1):
            instance_id = row["instance_id"]
            reference = "" if pd.isna(row["cypher"]) else str(row["cypher"])
            generated = (
                "" if pd.isna(row["generated_cypher"])
                else str(row["generated_cypher"])
            )
            alias = row.get("database_reference_alias")
            audit = (
                inventory.loc[instance_id]
                if instance_id in inventory.index else None
            )

            record = {
                "instance_id": instance_id,
                "database_reference_alias": alias,
                "database": "",
                "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
                "server_version": "",
                "logical_status": "",
                "comparison_mode": comparison_mode(reference, generated),
                "reference_row_count": None,
                "generated_row_count": None,
                "reference_columns": "",
                "generated_columns": "",
                "reference_error": "",
                "generated_error": "",
                "review_notes": "",
                "reference_preview": "",
                "generated_preview": "",
            }

            if not reference.strip() or not generated.strip():
                record["logical_status"] = "missing_query"
            elif instance_id not in syntax.index:
                record["logical_status"] = "syntax_validation_unavailable"
            elif syntax.loc[instance_id, "generated_status"] == "syntax_error":
                record["logical_status"] = "generated_syntax_error"
            elif syntax.loc[instance_id, "reference_status"] != "accepted":
                record["logical_status"] = "reference_syntax_not_accepted"
            elif (
                audit is not None
                and (
                    audit.get("reference_coverage_status")
                    == "reference_schema_inconsistency"
                    or audit.get("reference_logical_review_status")
                    == "confirmed_age_calculation_defect"
                )
            ):
                record["logical_status"] = "reference_defect_needs_review"
            elif pd.isna(alias) or not str(alias).strip():
                record["logical_status"] = "source_graph_unavailable"
            elif not str(alias).startswith(PREFIX):
                record["logical_status"] = "unrecognised_graph_alias"
            elif audit is None:
                record["logical_status"] = "schema_inventory_unavailable"
            else:
                database = str(alias)[len(PREFIX):]
                if database == "eoflix":
                    database = "neoflix"
                record["database"] = database

                populated, labels, types, version, error = check_graph(database)
                record["server_version"] = version

                if error:
                    record["logical_status"] = "graph_connection_failed"
                    record["review_notes"] = error
                elif not populated:
                    record["logical_status"] = "empty_source_graph"
                else:
                    # This checks available names, not full graph provenance,
                    # property types, relationship direction or completeness.
                    required_labels = set()
                    required_types = set()
                    for prefix in ("reference", "generated"):
                        required_labels.update(json.loads(
                            audit[f"{prefix}_node_labels"]
                        ))
                        required_types.update(json.loads(
                            audit[f"{prefix}_relationship_types"]
                        ))

                    missing_labels = required_labels - labels
                    missing_types = required_types - types

                    if missing_labels or missing_types:
                        record["logical_status"] = "graph_names_need_review"
                        record["review_notes"] = json.dumps({
                            "labels_absent_from_graph": sorted(missing_labels),
                            "types_absent_from_graph": sorted(missing_types),
                        })
                    else:
                        with drivers[database].session(
                            database=database,
                            default_access_mode=READ_ACCESS,
                        ) as session:
                            ref_result, ref_error = run_query(session, reference)
                            gen_result, gen_error = run_query(session, generated)

                        record["reference_error"] = ref_error
                        record["generated_error"] = gen_error

                        for prefix, result in (
                            ("reference", ref_result),
                            ("generated", gen_result),
                        ):
                            if result is not None:
                                columns, rows, preview = result
                                record[f"{prefix}_row_count"] = len(rows)
                                record[f"{prefix}_columns"] = json.dumps(columns)
                                record[f"{prefix}_preview"] = json.dumps(preview)

                        errors = (ref_error + " " + gen_error).lower()
                        if "row limit" in errors:
                            record["logical_status"] = "result_limit_inconclusive"
                        elif (
                            "timedout" in errors
                            or "timed out" in errors
                            or "timeout" in errors
                        ):
                            record["logical_status"] = "timeout_inconclusive"
                        elif ref_error:
                            record["logical_status"] = "reference_execution_failed"
                        elif gen_error:
                            record["logical_status"] = "generated_execution_failed"
                        else:
                            ref_columns, ref_rows, _ = ref_result
                            gen_columns, gen_rows, _ = gen_result

                            if not ref_rows and not gen_rows:
                                status = "both_empty_inconclusive"
                            elif len(ref_columns) != len(gen_columns):
                                status = "output_shape_differs_needs_review"
                            else:
                                if record["comparison_mode"] == "ordered_rows":
                                    match = ref_rows == gen_rows
                                else:
                                    match = Counter(ref_rows) == Counter(gen_rows)
                                status = (
                                    "observed_result_match"
                                    if match else "observed_result_difference"
                                )

                            record["logical_status"] = status
                            record["review_notes"] = (
                                "Compared columns by position, ignoring aliases. "
                                "No column remapping was performed. Result "
                                "differences require review for projection, "
                                "ordering and nondeterministic LIMIT effects. "
                                "Current live graphs may differ from the "
                                "dataset's original graph snapshots."
                            )

            records.append(record)
            save_results(records)
            print(
                f"[{position}/{len(queries)}] {instance_id}: "
                f"{record['logical_status']}",
                flush=True,
            )
    finally:
        for driver in drivers.values():
            driver.close()

    print("\nLOGICAL EVALUATION STATUS")
    print(
        pd.DataFrame(records)["logical_status"]
        .value_counts().to_string()
    )
    print(f"\nSaved: {OUTPUT}")
    print("Original generated_queries.csv was not changed.")


if __name__ == "__main__":
    run_logical_classifier()
