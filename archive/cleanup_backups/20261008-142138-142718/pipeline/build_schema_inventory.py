"""Extract schema declarations from the formats in our sample.

This is a schema inventory, not a Cypher query validator.
Unrecognised schemas are explicitly marked for review.
"""

import json
import re
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
INPUT = PROJECT / "data" / "generated_queries.csv"
OUTPUT = PROJECT / "outputs" / "schema_inventory.csv"

NAME = r"[A-Za-z_][A-Za-z0-9_]*"


def extract_schema(text):
    nodes = {}
    relationships = {}
    formats = set()

    def add(container, name, properties=()):
        container.setdefault(name, set()).update(properties)

    # Format 1: JSON schema with explicit node/relationship types.
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        parsed = None

    if isinstance(parsed, dict):
        for name, details in parsed.items():
            if not isinstance(details, dict):
                continue

            kind = details.get("type")
            properties = details.get("properties", {})
            properties = (
                properties.keys() if isinstance(properties, dict) else []
            )

            if kind == "node":
                add(nodes, name, properties)
                for rel, info in details.get("relationships", {}).items():
                    props = (
                        info.get("properties", {})
                        if isinstance(info, dict) else {}
                    )
                    add(
                        relationships,
                        rel,
                        props.keys() if isinstance(props, dict) else [],
                    )

            elif kind == "relationship":
                add(relationships, name, properties)

        if nodes or relationships:
            formats.add("json")

    # Format 2: Markdown headings and indented property declarations.
    section = None
    current = None

    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()

        if lower.startswith("node properties"):
            section, current = "node", None
            continue

        if lower.startswith("relationship properties"):
            section, current = "relationship", None
            continue

        if lower.startswith("the relationships"):
            section, current = None, None
            continue

        heading = re.fullmatch(
            rf"-\s*\*\*({NAME})\*\*", stripped
        )

        if heading and section:
            current = heading.group(1)
            container = nodes if section == "node" else relationships
            add(container, current)
            formats.add("markdown")
            continue

        property_match = re.match(
            rf"-\s*`({NAME})(?:`:\s*|:\s*[^`]+`)", stripped
        )

        if property_match and current and section:
            container = nodes if section == "node" else relationships
            add(container, current, [property_match.group(1)])

    # Format 3: Label {property: TYPE} declarations.
    # Split node and relationship property sections where supplied.
    boundary = re.search(
        r"Relationship properties", text, flags=re.IGNORECASE
    )
    node_text = text[:boundary.start()] if boundary else text
    rel_text = text[boundary.end():] if boundary else ""

    declaration = rf"(?<![A-Za-z0-9_])({NAME})\s*\{{([^{{}}]*)\}}"

    # Exclude relationship patterns from node extraction.
    node_declaration_text = re.sub(r"\[[^\]]*\]", "", node_text)
    for name, body in re.findall(declaration, node_declaration_text):
        properties = re.findall(rf"({NAME})\s*:", body)
        add(nodes, name, properties)
        formats.add("brace_declarations")

    for name, body in re.findall(declaration, rel_text):
        properties = re.findall(rf"({NAME})\s*:", body)
        add(relationships, name, properties)
        formats.add("brace_declarations")

    # Graph-pattern declarations, including property maps.
    for name, body in re.findall(
        rf"\(\s*:\s*({NAME})\s*(?:\{{([^{{}}]*)\}})?\s*\)", text
    ):
        add(nodes, name, re.findall(rf"({NAME})\s*:", body))
        formats.add("graph_patterns")

    for name, body in re.findall(
        rf"\[\s*:\s*({NAME})\s*(?:\{{([^{{}}]*)\}})?\s*\]", text
    ):
        add(relationships, name, re.findall(rf"({NAME})\s*:", body))
        formats.add("graph_patterns")

    # Format 4: Pipe-separated label : property, property declarations.
    if text.lstrip().startswith("|"):
        for piece in text.split("|"):
            match = re.fullmatch(
                rf"\s*({NAME})\s*:\s*(.*?)\s*", piece
            )
            if match:
                properties = [
                    value.strip()
                    for value in match.group(2).split(",")
                    if re.fullmatch(NAME, value.strip())
                ]
                add(nodes, match.group(1), properties)
                formats.add("pipe_declarations")
        # Bare labels in the functional dataset's schema format.
    bare_header = re.search(
        r"Relevant node labels and their properties\s+"
        r"(?:\(with datatypes\)\s*)?are:\s*(.*)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if bare_header:
        for line in bare_header.group(1).splitlines():
            label = line.strip()
            if re.fullmatch(NAME, label):
                add(nodes, label)
                formats.add("bare_node_labels")

    # Extract relationship types from dictionary-style declarations.
    relationship_section = re.search(
        r"Relevant relationships\s+are\s*:\s*(.*)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if relationship_section:
        dictionary_pattern = (
            r"['\"]type['\"]\s*:\s*['\"]?"
            r"([A-Za-z_][A-Za-z0-9_]*)"
            r"['\"]?\s*[,}]"
        )
        for relationship_name in re.findall(
            dictionary_pattern, relationship_section.group(1)
        ):
            add(relationships, relationship_name)
            formats.add("relationship_dictionary")
    
    return nodes, relationships, formats


def serialise(mapping):
    return json.dumps(
        {name: sorted(properties) for name, properties in sorted(mapping.items())},
        ensure_ascii=False,
    )


def main():
    df = pd.read_csv(INPUT)
    records = []

    for _, row in df.iterrows():
        text = "" if pd.isna(row["schema"]) else str(row["schema"])
        nodes, relationships, formats = extract_schema(text)

        records.append({
            "instance_id": row["instance_id"],
            "data_source": row["data_source"],
            "schema_status": (
                "extracted_needs_validation"
                if nodes else "unrecognised_needs_review"
            ),
            "formats": "; ".join(sorted(formats)),
            "node_count": len(nodes),
            "relationship_count": len(relationships),
            "node_properties": serialise(nodes),
            "relationship_properties": serialise(relationships),
        })

    results = pd.DataFrame(records)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT, index=False)

    print("SCHEMA EXTRACTION STATUS")
    print(results["schema_status"].value_counts().to_string())

    print("\nCOVERAGE BY SOURCE")
    print(
        results.groupby("data_source").agg(
            records=("instance_id", "size"),
            schemas_with_nodes=("node_count", lambda values: (values > 0).sum()),
        ).to_string()
    )

    print(f"\nSaved to: {OUTPUT}")
    print("Existing queries and classifications were not changed.")
    print("Extraction success still requires validation against source schemas.")


if __name__ == "__main__":
    main()