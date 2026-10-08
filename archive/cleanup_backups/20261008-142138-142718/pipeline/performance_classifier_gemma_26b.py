"""
Inspect generated and reference query plans on source graphs.

EXPLAIN findings are potential concerns, not measured inefficiency.
Gemma adaptation of the existing Gemini evaluator.
Only input/output paths change; measurement logic remains identical.
Original queries and classifications are never modified.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from neo4j import Query, READ_ACCESS

try:
    from .logical_classifier import get_driver
except ImportError:
    from logical_classifier import get_driver

PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT / "outputs/gemma_26b_performance_validation.csv"
PREFIX = "neo4jlabs_demo_db_"


def inspect_plan(session, query):
    try:
        summary = session.run(
            Query("EXPLAIN " + query, timeout=30)
        ).consume()

        if summary.query_type != "r":
            raise ValueError("Statement is not classified as read-only.")

        if summary.plan is None:
            raise ValueError("Neo4j returned no execution plan.")

        operators = []
        estimates = []

        def walk(plan):
            operator = str(plan.get("operatorType", "unknown"))
            operators.append(operator)

            arguments = plan.get("args", {})
            estimate = arguments.get("EstimatedRows")
            if estimate is not None:
                estimates.append({
                    "operator": operator,
                    "estimated_rows": estimate,
                })

            for child in plan.get("children", []):
                walk(child)

        walk(summary.plan)

        # Operator names can contain planner suffixes.
        base_names = {
            operator.split("@", 1)[0] for operator in operators
        }

        scans = sorted(
            operator for operator in base_names
            if "Scan" in operator
        )
        index_operators = sorted(
            operator for operator in base_names
            if "Index" in operator
        )
        cartesian = any(
            "CartesianProduct" in operator for operator in base_names
        )

        return {
            "status": "plan_available",
            "operators": json.dumps(operators),
            "scan_operators": json.dumps(scans),
            "index_operators": json.dumps(index_operators),
            "cartesian_product": cartesian,
            "estimated_rows": json.dumps(estimates, default=str),
            "plan": json.dumps(summary.plan, default=str),
            "server_version": summary.server.agent,
            "error": "",
        }

    except Exception as error:
        return {
            "status": "plan_failed",
            "error": (
                f"{getattr(error, 'code', type(error).__name__)}: {error}"
            )[:1000],
        }


def save_results(records):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp")
    pd.DataFrame(records).to_csv(temporary, index=False)
    temporary.replace(OUTPUT)


def run_performance_classifier():
    queries = pd.read_csv(PROJECT / "outputs/benchmark_gemma_26b.csv")
    syntax = pd.read_csv(
        PROJECT / "outputs/gemma_26b_syntax_validation.csv"
    )
    logical = pd.read_csv(PROJECT / "outputs/gemma_26b_logical_validation.csv")

    for name, frame in (
        ("queries", queries),
        ("syntax", syntax),
        ("logical", logical),
    ):
        if frame["instance_id"].isna().any():
            raise ValueError(f"Missing IDs in {name}.")
        if frame["instance_id"].duplicated().any():
            raise ValueError(f"Duplicate IDs in {name}.")

    syntax = syntax.set_index("instance_id")
    logical = logical.set_index("instance_id")

    drivers = {}
    records = []

    try:
        for position, (_, row) in enumerate(queries.iterrows(), 1):
            instance_id = row["instance_id"]
            alias = row.get("database_reference_alias")
            query = (
                "" if pd.isna(row["generated_cypher"])
                else str(row["generated_cypher"])
            )
            reference = (
                "" if pd.isna(row["cypher"]) else str(row["cypher"])
            )

            logical_status = (
                logical.loc[instance_id, "logical_status"]
                if instance_id in logical.index else "unavailable"
            )

            record = {
                "instance_id": instance_id,
                "database_reference_alias": alias,
                "database": "",
                "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
                "logical_status": logical_status,
                "performance_status": "",
                "measurement_method": "EXPLAIN",
                "measured_inefficiency": "not_assessed",
                "review_notes": (
                    "Scans and absent index operators are descriptive. "
                    "They do not establish missing indexes or inefficiency. "
                    "Estimated rows are not measured rows. Observed result "
                    "agreement does not establish full logical correctness."
                ),
            }

            if not query.strip():
                record["performance_status"] = "missing_generated_query"
            elif instance_id not in syntax.index:
                record["performance_status"] = "syntax_validation_unavailable"
            elif syntax.loc[instance_id, "generated_status"] == "syntax_error":
                record["performance_status"] = "generated_syntax_error"
            elif pd.isna(alias) or not str(alias).strip():
                record["performance_status"] = "source_graph_unavailable"
            elif not str(alias).startswith(PREFIX):
                record["performance_status"] = "unrecognised_graph_alias"
            elif logical_status in {
                "graph_connection_failed",
                "empty_source_graph",
                "graph_names_need_review",
                "schema_inventory_unavailable",
            }:
                record["performance_status"] = (
                    "source_graph_not_ready_for_plan_review"
                )
            else:
                database = str(alias)[len(PREFIX):]
                if database == "eoflix":
                    database = "neoflix"
                record["database"] = database

                try:
                    if database not in drivers:
                        drivers[database] = get_driver(database)

                    with drivers[database].session(
                        database=database,
                        default_access_mode=READ_ACCESS,
                    ) as session:
                        generated_plan = inspect_plan(session, query)
                        reference_plan = (
                            inspect_plan(session, reference)
                            if reference.strip()
                            else {
                                "status": "missing_query",
                                "error": "",
                            }
                        )

                    for prefix, plan in (
                        ("generated", generated_plan),
                        ("reference", reference_plan),
                    ):
                        for key, value in plan.items():
                            record[f"{prefix}_{key}"] = value

                    if generated_plan["status"] != "plan_available":
                        record["performance_status"] = "generated_plan_failed"
                    elif generated_plan["cartesian_product"]:
                        record["performance_status"] = (
                            "potential_cartesian_product_needs_review"
                        )
                    else:
                        record["performance_status"] = (
                            "plan_inspected_no_cartesian_product"
                        )

                except Exception as error:
                    record["performance_status"] = "graph_connection_failed"
                    record["generated_error"] = (
                        f"{type(error).__name__}: {error}"
                    )[:1000]

            records.append(record)
            save_results(records)
            print(
                f"[{position}/{len(queries)}] {instance_id}: "
                f"{record['performance_status']}",
                flush=True,
            )

    finally:
        for driver in drivers.values():
            driver.close()

    results = pd.DataFrame(records)
    print("\nPERFORMANCE PLAN STATUS")
    print(results["performance_status"].value_counts().to_string())
    print(f"\nSaved: {OUTPUT}")
    print("Measured inefficiency: not assessed by EXPLAIN.")
    print("Original queries and classifications were not changed.")



# Bounded PROFILE measurements
def run_profile_measurements():
    import argparse
    import hashlib
    import socket
    import time
    from collections import Counter
    from datetime import datetime, timezone
    from neo4j import READ_ACCESS, unit_of_work
    from logical_classifier import canonical, comparison_mode

    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--max-cases", type=int, default=5)
    args = parser.parse_args()
    if args.max_cases < 1:
        raise ValueError("--max-cases must be positive.")

    project = Path(__file__).resolve().parents[1]
    outputs = project / "outputs"
    queries = pd.read_csv(
        project / "outputs/benchmark_gemma_26b.csv", keep_default_na=False
    )
    logical = pd.read_csv(
        outputs / "gemma_26b_logical_validation.csv", keep_default_na=False
    )

    for frame in (queries, logical):
        if frame["instance_id"].eq("").any():
            raise ValueError("Missing instance ID.")
        if frame["instance_id"].duplicated().any():
            raise ValueError("Duplicate instance ID.")
    if set(queries["instance_id"]) != set(logical["instance_id"]):
        raise ValueError("Logical and query IDs differ.")

    eligible = logical.loc[
        logical["logical_status"].eq("observed_result_match"),
        ["instance_id", "database"],
    ].merge(queries, on="instance_id", validate="one_to_one")

    eligible = eligible.sort_values("instance_id").head(args.max_cases)
    if eligible.empty:
        raise ValueError("No previously matching query pairs available.")

    target = outputs / "gemma_26b_performance_profile.csv"
    if target.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target.with_name(
            f"gemma_26b_performance_profile.{stamp}.csv"
        ).write_bytes(target.read_bytes())

    def digest(value):
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def plan_hits(plan):
        if not plan:
            return 0
        return int(plan.get("dbHits", 0) or 0) + sum(
            plan_hits(child) for child in plan.get("children", [])
        )

    @unit_of_work(timeout=15)
    def measure(tx, query):
        # EXPLAIN first: reject queries that are not classified read-only.
        check = tx.run("EXPLAIN " + query).consume()
        if check.query_type != "r":
            raise ValueError("Query is not classified read-only.")

        started = time.perf_counter()
        result = tx.run("PROFILE " + query)
        columns = list(result.keys())
        values = []
        for record in result:
            if len(values) >= 5000:
                raise ValueError("Result exceeds the 5000-row measurement limit.")
            values.append(tuple(canonical(value) for value in record.values()))
        summary = result.consume()
        elapsed = (time.perf_counter() - started) * 1000

        if summary.profile is None:
            raise ValueError("No PROFILE plan returned.")

        return {
            "values": values,
            "column_count": len(columns),
            "returned_rows": len(values),
            "db_hits": plan_hits(summary.profile),
            "client_elapsed_profile_ms": round(elapsed, 3),
            "server_result_available_ms": summary.result_available_after,
            "server_result_consumed_ms": summary.result_consumed_after,
            "server_version": summary.server.agent,
        }

    records = []
    def checkpoint():
        temporary = target.with_name(target.name + ".tmp")
        pd.DataFrame(records).to_csv(temporary, index=False)
        temporary.replace(target)

    print(f"Previously matching pairs selected: {len(eligible)}", flush=True)
    print("Each pair: one warm-up and three measured repetitions.", flush=True)

    for case_number, (_, row) in enumerate(eligible.iterrows(), 1):
        driver = None
        database = row["database"]
        queries_by_kind = {
            "reference": row["cypher"],
            "generated": row["generated_cypher"],
        }
        mode = comparison_mode(row["cypher"], row["generated_cypher"])

        try:
            driver = get_driver(database)
            driver.verify_connectivity()
            with driver.session(
                database=database, default_access_mode=READ_ACCESS
            ) as session:
                for repetition in range(4):
                    phase = "warmup" if repetition == 0 else "measurement"
                    order = (
                        ("reference", "generated")
                        if repetition % 2 == 0
                        else ("generated", "reference")
                    )
                    successful = {}
                    pair_records = []

                    for kind in order:
                        query = queries_by_kind[kind]
                        record = {
                            "instance_id": row["instance_id"],
                            "database": database,
                            "phase": phase,
                            "repetition": repetition,
                            "query_kind": kind,
                            "query_sha256": digest(query),
                            "evaluated_at_utc": datetime.now(
                                timezone.utc
                            ).isoformat(),
                            "execution_node": socket.gethostname(),
                            "comparison_mode": mode,
                            "profile_status": "",
                            "current_pair_result_match": "",
                            "error": "",
                        }
                        try:
                            measured = session.execute_read(measure, query)
                            successful[kind] = measured
                            record.update({
                                key: value for key, value in measured.items()
                                if key != "values"
                            })
                            record["profile_status"] = "measured"
                        except Exception as error:
                            record["profile_status"] = "inconclusive"
                            record["error"] = (
                                type(error).__name__ + ": " + str(error)
                            )[:1000]
                        pair_records.append(record)

                    if len(successful) == 2:
                        reference = successful["reference"]
                        generated = successful["generated"]
                        same_shape = (
                            reference["column_count"]
                            == generated["column_count"]
                        )
                        if mode == "ordered_rows":
                            same_values = (
                                reference["values"] == generated["values"]
                            )
                        else:
                            same_values = (
                                Counter(reference["values"])
                                == Counter(generated["values"])
                            )
                        for record in pair_records:
                            record["current_pair_result_match"] = int(
                                same_shape and same_values
                            )

                    records.extend(pair_records)
                    checkpoint()

        except Exception as error:
            records.append({
                "instance_id": row["instance_id"],
                "database": database,
                "phase": "connection",
                "profile_status": "inconclusive",
                "error": (type(error).__name__ + ": " + str(error))[:1000],
            })
            checkpoint()
        finally:
            if driver is not None:
                driver.close()

        print(
            f"[{case_number}/{len(eligible)}] {row['instance_id']}: recorded",
            flush=True,
        )

    saved = pd.DataFrame(records)
    print("\nPROFILE STATUS")
    print(saved["profile_status"].value_counts().to_string())
    print(f"Saved: {target}")
    print("Warm-up rows must be excluded from reported measurement averages.")
    print("Client timing includes network transfer and PROFILE overhead.")
    print("No binary inefficiency label is assigned.")
    print("Original queries and EXPLAIN evidence were not changed.")



def summarise_profile_measurements():
    """Validate saved PROFILE runs and summarise measured repetitions."""
    import hashlib
    import numpy as np

    source = PROJECT / "outputs/gemma_26b_performance_profile.csv"
    target = PROJECT / "outputs/gemma_26b_performance_profile_summary.csv"
    query_path = PROJECT / "outputs/benchmark_gemma_26b.csv"

    runs = pd.read_csv(source, keep_default_na=False)
    queries = pd.read_csv(query_path, keep_default_na=False)

    required = {
        "instance_id", "database", "phase", "repetition", "query_kind",
        "query_sha256", "profile_status", "current_pair_result_match",
        "returned_rows", "db_hits", "client_elapsed_profile_ms",
    }
    missing = required - set(runs.columns)
    if missing:
        raise ValueError(f"Missing measurement columns: {sorted(missing)}")

    if queries["instance_id"].eq("").any():
        raise ValueError("Missing source query IDs.")
    if queries["instance_id"].duplicated().any():
        raise ValueError("Duplicate source query IDs.")
    if runs["instance_id"].eq("").any():
        raise ValueError("Missing measurement IDs.")
    if runs.empty:
        raise ValueError("No saved measurements.")

    if not runs["profile_status"].eq("measured").all():
        raise ValueError(
            "Some runs are inconclusive. Review them before summarising."
        )

    if not runs["phase"].isin(["warmup", "measurement"]).all():
        raise ValueError("Unexpected measurement phase.")
    if not runs["query_kind"].isin(["reference", "generated"]).all():
        raise ValueError("Unexpected query kind.")

    for column in (
        "repetition", "current_pair_result_match", "returned_rows",
        "db_hits", "client_elapsed_profile_ms",
    ):
        runs[column] = pd.to_numeric(runs[column], errors="raise")
        if not np.isfinite(runs[column]).all():
            raise ValueError(f"Non-finite values in {column}.")

    for column in ("repetition", "returned_rows", "db_hits"):
        if not runs[column].mod(1).eq(0).all():
            raise ValueError(f"Non-integer values in {column}.")

    if (runs[["returned_rows", "db_hits",
              "client_elapsed_profile_ms"]] < 0).any().any():
        raise ValueError("Negative measurement values.")

    keys = ["instance_id", "query_kind", "phase", "repetition"]
    if runs.duplicated(keys).any():
        raise ValueError("Duplicate measurement runs.")

    # Verify that the saved measurements refer to the current query text.
    source_queries = queries.set_index("instance_id")
    for (instance_id, kind), group in runs.groupby(
        ["instance_id", "query_kind"]
    ):
        if instance_id not in source_queries.index:
            raise ValueError(f"Unknown query ID: {instance_id}")

        column = "cypher" if kind == "reference" else "generated_cypher"
        query = str(source_queries.loc[instance_id, column])
        expected_hash = hashlib.sha256(
            query.encode("utf-8")
        ).hexdigest()

        if not group["query_sha256"].eq(expected_hash).all():
            raise ValueError(
                f"Saved measurements use different query text: "
                f"{instance_id}, {kind}"
            )

    expected_runs = {
        (kind, phase, repetition)
        for kind in ("reference", "generated")
        for phase, repetitions in (
            ("warmup", [0]),
            ("measurement", [1, 2, 3]),
        )
        for repetition in repetitions
    }

    for instance_id, group in runs.groupby("instance_id"):
        actual_runs = set(zip(
            group["query_kind"], group["phase"], group["repetition"]
        ))
        if actual_runs != expected_runs:
            raise ValueError(
                f"Incomplete repetition schedule: {instance_id}"
            )
        if group["database"].nunique() != 1 or group["database"].eq("").any():
            raise ValueError(f"Inconsistent database: {instance_id}")

        for column in ("server_version", "execution_node", "comparison_mode"):
            if column in group.columns and group[column].nunique() != 1:
                raise ValueError(
                    f"Inconsistent {column} within pair: {instance_id}"
                )

    measured = runs.loc[runs["phase"].eq("measurement")].copy()
    pair_agreement = measured.groupby("instance_id").apply(
        lambda group: bool(
            group["current_pair_result_match"].eq(1).all()
            and group["returned_rows"].gt(0).all()
        )
    )

    summary = measured.groupby(
        ["instance_id", "database", "query_kind"], as_index=False
    ).agg(
        repetitions=("repetition", "size"),
        returned_rows_min=("returned_rows", "min"),
        returned_rows_max=("returned_rows", "max"),
        db_hits_median=("db_hits", "median"),
        db_hits_min=("db_hits", "min"),
        db_hits_max=("db_hits", "max"),
        client_elapsed_profile_ms_median=("client_elapsed_profile_ms", "median"),
        client_elapsed_profile_ms_min=("client_elapsed_profile_ms", "min"),
        client_elapsed_profile_ms_max=("client_elapsed_profile_ms", "max"),
    )

    summary["all_repetitions_nonempty_result_match"] = (
        summary["instance_id"].map(pair_agreement)
    )
    summary = summary.sort_values(
        ["instance_id", "query_kind"]
    ).reset_index(drop=True)

    # Preserve the previous summary before replacing it.
    if target.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = target.with_name(
            f"gemma_26b_performance_profile_summary.before_rebuild_{stamp}.csv"
        )
        backup.write_bytes(target.read_bytes())

    temporary = target.with_suffix(".tmp")
    summary.to_csv(temporary, index=False)
    temporary.replace(target)

    print("PERFORMANCE SUMMARY REBUILT")
    print("Total saved runs:", len(runs))
    print("Warm-ups excluded:", runs["phase"].eq("warmup").sum())
    print("Measured runs:", len(measured))
    print("Query pairs:", measured["instance_id"].nunique())
    print("Summary rows:", len(summary))
    print("Pairs matching with non-empty results in every measured repetition:",
          int(pair_agreement.sum()))
    print("Other pairs:", int((~pair_agreement).sum()))
    print("PASS: query hashes and repetition schedules verified.")
    print("Saved:", target)
    print("No database queries were executed.")
    print("Original queries and raw measurements were not changed.")
    print("Timing includes network transfer and PROFILE overhead.")


if __name__ == "__main__":
    import sys

    if "--summarise" in sys.argv:
        if len(sys.argv) != 2:
            raise SystemExit("Use --summarise by itself.")
        summarise_profile_measurements()
    elif "--profile" in sys.argv:
        run_profile_measurements()
    else:
        run_performance_classifier()
