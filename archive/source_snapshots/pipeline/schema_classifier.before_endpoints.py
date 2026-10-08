"""
Repeatable preliminary schema checks.

Checks explicit node labels, relationship types and simple
variable.property expressions against the supplied schema inventory.
Preserves existing review notes and original queries.

This is a conservative text check, not a complete Cypher parser.
"""
import json
import re
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
INPUT = PROJECT / "data/generated_queries.csv"
OUTPUT = PROJECT / "outputs/schema_inventory.csv"

IDENTIFIER = r"(?:`(?:``|[^`])+`|[A-Za-z_][A-Za-z0-9_]*)"


def clean_name(value):
    if value.startswith("`"):
        return value[1:-1].replace("``", "`")
    return value


def visible_query(query):
    """Hide string literals and comments while retaining backtick names."""
    pattern = re.compile(
        r"`(?:``|[^`])*`"
        r"| '(?:\\.|''|[^'\\])*'"
        r'| "(?:\\.|""|[^"\\])*"'
        r"| //[^\n]*"
        r"| /\*[\s\S]*?\*/",
        re.VERBOSE,
    )
    return pattern.sub(
        lambda match: (
            match.group(0)
            if match.group(0).startswith("`")
            else " " * len(match.group(0))
        ),
        str(query),
    )


def detected_names(query):
    text = visible_query(query)
    labels, types = set(), set()

    # Conventional explicit node patterns, including multiple labels.
    node = re.compile(
        rf"\(\s*(?:{IDENTIFIER}\s*)?"
        rf"(?P<labels>(?::\s*{IDENTIFIER}\s*)+)"
    )
    for match in node.finditer(text):
        labels.update(
            clean_name(name)
            for name in re.findall(
                rf":\s*({IDENTIFIER})", match.group("labels")
            )
        )

    # Conventional relationship patterns, including type alternatives.
    relationship = re.compile(
        rf"\[\s*(?:{IDENTIFIER}\s*)?:\s*"
        rf"(?P<types>{IDENTIFIER}"
        rf"(?:\s*\|\s*:?\s*{IDENTIFIER})*)"
    )
    for match in relationship.finditer(text):
        types.update(
            clean_name(name)
            for name in re.findall(IDENTIFIER, match.group("types"))
        )

    # Exclude namespaced function calls such as duration.inDays(...).
    properties = set()
    for match in re.finditer(
        rf"(?<![A-Za-z0-9_`])({IDENTIFIER})\s*\.\s*({IDENTIFIER})",
        text,
    ):
        following = text[match.end():].lstrip()
        if not following.startswith("("):
            properties.add(clean_name(match.group(2)))


    # Include static property keys inside node/relationship pattern maps.
    pattern_maps = re.compile(
        rf"(?:\(|\[)\s*(?:{IDENTIFIER}\s*)?"
        rf"(?::\s*{IDENTIFIER}\s*)*"
        rf"\{{([^{{}}]*)\}}"
    )
    for match in pattern_maps.finditer(text):
        for key in re.finditer(
            rf"(?:^|,)\s*({IDENTIFIER})\s*:",
            match.group(1),
        ):
            properties.add(clean_name(key.group(1)))

    return labels, types, properties


def encode(values):
    return json.dumps(sorted(values), ensure_ascii=False)


def read_checked(path):
    frame = pd.read_csv(path, keep_default_na=False)
    if "instance_id" not in frame.columns:
        raise ValueError(f"Missing instance_id: {path.name}")
    if frame["instance_id"].eq("").any():
        raise ValueError(f"Empty instance ID: {path.name}")
    if frame["instance_id"].duplicated().any():
        raise ValueError(f"Duplicate instance ID: {path.name}")
    return frame


def run_schema_classifier():
    queries = read_checked(INPUT)
    inventory = read_checked(OUTPUT)

    if set(queries["instance_id"]) != set(inventory["instance_id"]):
        raise ValueError("Query and inventory IDs do not match.")

    queries = queries.set_index("instance_id")
    result = inventory.copy()

    for index, row in result.iterrows():
        query = queries.loc[row["instance_id"]]
        nodes = json.loads(row["node_properties"])
        relationships = json.loads(row["relationship_properties"])
        known_properties = {
            name
            for mapping in (nodes, relationships)
            for properties in mapping.values()
            for name in properties
        }

        for prefix, column in (
            ("reference", "cypher"),
            ("generated", "generated_cypher"),
        ):
            labels, types, properties = detected_names(query[column])
            missing_labels = labels - set(nodes)
            missing_types = types - set(relationships)

            result.at[index, f"{prefix}_node_labels"] = encode(labels)
            result.at[index, f"{prefix}_relationship_types"] = encode(types)
            result.at[index, f"{prefix}_labels_not_in_inventory"] = encode(
                missing_labels
            )
            result.at[index, f"{prefix}_types_not_in_inventory"] = encode(
                missing_types
            )

            if not labels and not types:
                status = "no_explicit_names_detected"
            elif missing_labels or (relationships and missing_types):
                status = "needs_review"
            elif types and not relationships:
                status = (
                    "relationship_schema_unavailable"
                    if prefix == "reference"
                    else "partial_check_relationship_schema_unavailable"
                )
            else:
                status = "detected_names_covered"

            if prefix == "reference":
                previous = row.get("reference_coverage_status", "")
                if (
                    previous == "reference_schema_inconsistency"
                    and status == "needs_review"
                ):
                    status = "reference_schema_inconsistency"
                result.at[index, "reference_coverage_status"] = status
            else:
                result.at[index, "generated_name_coverage_status"] = status
                result.at[index, "generated_relationship_check"] = (
                    "not_assessable_from_supplied_schema"
                    if types and not relationships
                    else "detected_type_names_checked"
                )
                missing_properties = properties - known_properties
                result.at[index, "generated_static_property_names"] = encode(
                    properties
                )
                result.at[
                    index, "generated_properties_not_in_inventory"
                ] = encode(missing_properties)
                result.at[index, "generated_property_name_status"] = (
                    "no_static_property_names_detected"
                    if not properties
                    else "candidate_property_mismatch_needs_review"
                    if missing_properties
                    else "detected_names_present_somewhere_in_schema"
                )

    backup = OUTPUT.with_name("schema_inventory.before_repeatable_checks.csv")
    if not backup.exists():
        backup.write_bytes(OUTPUT.read_bytes())

    temporary = OUTPUT.with_name(OUTPUT.name + ".tmp")
    result.to_csv(temporary, index=False)
    temporary.replace(OUTPUT)

    for column in (
        "reference_coverage_status",
        "generated_name_coverage_status",
        "generated_property_name_status",
    ):
        print(f"\n{column.upper()}")
        print(result[column].value_counts().to_string())

    candidates = result[
        result["generated_property_name_status"].eq(
            "candidate_property_mismatch_needs_review"
        )
        | result["generated_name_coverage_status"].eq("needs_review")
    ]
    print(f"\nGenerated candidates requiring review: {len(candidates)}")
    if not candidates.empty:
        print(candidates[[
            "instance_id",
            "generated_labels_not_in_inventory",
            "generated_types_not_in_inventory",
            "generated_properties_not_in_inventory",
        ]].to_string(index=False))

    print(f"\nRecords checked: {len(result)}")
    print("Existing review notes were retained.")
    print("Original queries and database data were not changed.")
    print("Simple pattern-map keys are checked. Property ownership, "
          "scope, dynamic expressions and direction are not fully checked.")


if __name__ == "__main__":
    run_schema_classifier()
