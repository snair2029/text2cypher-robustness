import pandas as pd
import re
import json
import os

def extract_schema_elements(schema_str):
    """
    Extract node labels, relationship types and property names
    from the schema string.
    """
    node_labels = set()
    relationship_types = set()
    property_names = set()

    if not schema_str or str(schema_str).strip() == '':
        return node_labels, relationship_types, property_names

    schema_str = str(schema_str)

    # Extract node labels - pattern: (label) or :Label or **Label**
    node_patterns = [
        r'\*\*(\w+)\*\*',           # **NodeLabel**
        r':\s*([A-Z][a-zA-Z_]*)',   # :NodeLabel
        r'\(([A-Z][a-zA-Z_]*)\)',   # (NodeLabel)
    ]
    for pattern in node_patterns:
        matches = re.findall(pattern, schema_str)
        node_labels.update(matches)

    # Extract relationship types - pattern: [:REL_TYPE] or -[:REL]-
    rel_patterns = [
        r'\[:([A-Z_]+)\]',          # [:REL_TYPE]
        r'-\[:([A-Z_]+)\]',         # -[:REL_TYPE]
        r'"([A-Z_]+)":\s*{[^}]*"type":\s*"relationship"',  # JSON format
    ]
    for pattern in rel_patterns:
        matches = re.findall(pattern, schema_str)
        relationship_types.update(matches)

    # Extract property names
    prop_patterns = [
        r'`(\w+)`:\s*(?:STRING|INTEGER|FLOAT|BOOLEAN|DATE)',  # `prop`: TYPE
        r'"(\w+)":\s*{[^}]*"type"',   # JSON format
        r'- `(\w+)`',                  # - `property`
    ]
    for pattern in prop_patterns:
        matches = re.findall(pattern, schema_str)
        property_names.update(matches)

    return node_labels, relationship_types, property_names

def extract_query_elements(query_str):
    """
    Extract node labels, relationship types and properties
    used in the generated query.
    """
    node_labels = set()
    relationship_types = set()
    property_names = set()

    if not query_str or str(query_str).strip() == '':
        return node_labels, relationship_types, property_names

    query_str = str(query_str)

    # Extract node labels from query - (n:Label) or (:Label)
    node_matches = re.findall(r'\(\w*:([A-Za-z_]\w*)', query_str)
    node_labels.update(node_matches)

    # Extract relationship types - [:REL_TYPE]
    rel_matches = re.findall(r'\[:([A-Z_]+)\]', query_str)
    relationship_types.update(rel_matches)

    # Extract property names - n.property
    prop_matches = re.findall(r'\w+\.([a-zA-Z_]\w*)', query_str)
    property_names.update(prop_matches)

    return node_labels, relationship_types, property_names

def check_schema_hallucination(query, schema):
    """
    Check if the query uses elements not present in the schema.
    Returns (is_hallucination, details)
    """
    schema_nodes, schema_rels, schema_props = extract_schema_elements(schema)
    query_nodes, query_rels, query_props = extract_query_elements(query)

    hallucinated = []

    # Check node labels
    if schema_nodes:
        for node in query_nodes:
            if node not in schema_nodes and node.lower() not in \
               {s.lower() for s in schema_nodes}:
                hallucinated.append(f"Node label not in schema: {node}")

    # Check relationship types
    if schema_rels:
        for rel in query_rels:
            if rel not in schema_rels:
                hallucinated.append(f"Relationship not in schema: {rel}")

    if hallucinated:
        return True, "; ".join(hallucinated)
    return False, ""

def run_schema_classifier():
    df = pd.read_csv("data/generated_queries.csv")
    df['generated_cypher'] = df['generated_cypher'].fillna('')
    df['schema'] = df['schema'].fillna('')

    if 'schema_hallucination' not in df.columns:
        df['schema_hallucination'] = 0
    if 'schema_hallucination_msg' not in df.columns:
        df['schema_hallucination_msg'] = ''

    print("Running schema hallucination classifier on 200 queries...")
    print("="*50)

    hallucination_count = 0

    for i, row in df.iterrows():
        query = row['generated_cypher']
        schema = row['schema']

        if not query or query.strip() == '':
            df.at[i, 'schema_hallucination'] = 0
            continue

        is_hallucination, msg = check_schema_hallucination(query, schema)

        if is_hallucination:
            df.at[i, 'schema_hallucination'] = 1
            df.at[i, 'schema_hallucination_msg'] = msg[:300]
            hallucination_count += 1
            print(f"[{i+1}] HALLUCINATION — {msg[:80]}")
            print(f"     Q: {row['question'][:60]}...")
        else:
            df.at[i, 'schema_hallucination'] = 0
            df.at[i, 'schema_hallucination_msg'] = ''

    df.to_csv("data/generated_queries.csv", index=False)

    print("="*50)
    print(f"Schema hallucinations found: {hallucination_count}/200")
    print(f"Schema-conformant queries: {200 - hallucination_count}/200")
    print("Results saved to data/generated_queries.csv")

if __name__ == "__main__":
    run_schema_classifier()