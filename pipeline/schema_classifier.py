import pandas as pd
import re

# ─────────────────────────────────────────
# SCHEMA EXTRACTION
# ─────────────────────────────────────────

def extract_schema_elements(schema_str):
    """
    Parse the schema string and return sets of known
    node labels, relationship types, and property names.
    Handles multiple schema formats (markdown, JSON, table).
    """
    node_labels = set()
    relationship_types = set()
    property_names = set()

    if not schema_str or str(schema_str).strip() == '':
        return node_labels, relationship_types, property_names

    schema_str = str(schema_str)

    # Node labels — matches **Label**, :Label, (Label)
    for pattern in [
        r'\*\*(\w+)\*\*',
        r':\s*([A-Z][a-zA-Z_]*)',
        r'\(([A-Z][a-zA-Z_]*)\)',
    ]:
        node_labels.update(re.findall(pattern, schema_str))

    # Relationship types — matches [:REL_TYPE]
    for pattern in [
        r'\[:([A-Z_]+)\]',
        r'-\[:([A-Z_]+)\]',
        r'"([A-Z_]+)":\s*{[^}]*"type":\s*"relationship"',
    ]:
        relationship_types.update(re.findall(pattern, schema_str))

    # Property names — matches `prop`: TYPE or JSON format
    for pattern in [
        r'`(\w+)`:\s*(?:STRING|INTEGER|FLOAT|BOOLEAN|DATE)',
        r'"(\w+)":\s*{[^}]*"type"',
        r'- `(\w+)`',
    ]:
        property_names.update(re.findall(pattern, schema_str))

    return node_labels, relationship_types, property_names


# ─────────────────────────────────────────
# QUERY EXTRACTION
# ─────────────────────────────────────────

def extract_query_elements(query_str):
    """
    Parse the generated Cypher query and return sets of
    node labels, relationship types, and properties used.
    """
    node_labels = set()
    relationship_types = set()
    property_names = set()

    if not query_str or str(query_str).strip() == '':
        return node_labels, relationship_types, property_names

    query_str = str(query_str)

    node_labels.update(re.findall(r'\(\w*:([A-Za-z_]\w*)', query_str))
    relationship_types.update(re.findall(r'\[:([A-Z_]+)\]', query_str))
    property_names.update(re.findall(r'\w+\.([a-zA-Z_]\w*)', query_str))

    return node_labels, relationship_types, property_names


# ─────────────────────────────────────────
# HALLUCINATION CHECK
# ─────────────────────────────────────────

def check_schema_hallucination(query, schema):
    """
    Compare query elements against schema elements.
    Returns (is_hallucination: bool, detail_message: str)
    """
    schema_nodes, schema_rels, _ = extract_schema_elements(schema)
    query_nodes, query_rels, _ = extract_query_elements(query)

    issues = []

    if schema_nodes:
        schema_nodes_lower = {s.lower() for s in schema_nodes}
        for node in query_nodes:
            if node.lower() not in schema_nodes_lower:
                issues.append(f"Node not in schema: {node}")

    if schema_rels:
        for rel in query_rels:
            if rel not in schema_rels:
                issues.append(f"Relationship not in schema: {rel}")

    if issues:
        return True, "; ".join(issues)
    return False, ""


# ─────────────────────────────────────────
# MAIN CLASSIFIER
# ─────────────────────────────────────────

def run_schema_classifier():
    df = pd.read_csv("data/generated_queries.csv")
    df['generated_cypher'] = df['generated_cypher'].fillna('')
    df['schema'] = df['schema'].fillna('')

    if 'schema_hallucination' not in df.columns:
        df['schema_hallucination'] = 0
    if 'schema_hallucination_msg' not in df.columns:
        df['schema_hallucination_msg'] = ''

    print("Schema Hallucination Classifier")
    print("="*50)

    hallucination_count = 0

    for i, row in df.iterrows():
        query = row['generated_cypher']
        schema = row['schema']

        if not query or query.strip() == '':
            df.at[i, 'schema_hallucination'] = 0
            continue

        is_error, msg = check_schema_hallucination(query, schema)

        df.at[i, 'schema_hallucination'] = 1 if is_error else 0
        df.at[i, 'schema_hallucination_msg'] = msg[:300] if is_error else ''

        if is_error:
            hallucination_count += 1
            print(f"[{i+1}] HALLUCINATION | {msg[:80]}")
            print(f"      {row['question'][:70]}")

    df.to_csv("data/generated_queries.csv", index=False)

    print("="*50)
    print(f"Schema hallucinations : {hallucination_count} / 200")
    print(f"Schema-conformant     : {200 - hallucination_count} / 200")
    print("Saved → data/generated_queries.csv")


if __name__ == "__main__":
    run_schema_classifier()