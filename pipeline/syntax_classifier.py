import pandas as pd
import re
import os

def check_syntax(query):
    """
    Check for basic Cypher syntax errors using pattern matching.
    Returns (is_error, error_message)
    """
    if not query or query.strip() == '':
        return True, "Empty query"

    query = query.strip()

    # Check for unmatched parentheses
    if query.count('(') != query.count(')'):
        return True, "Unmatched parentheses"

    # Check for unmatched square brackets
    if query.count('[') != query.count(']'):
        return True, "Unmatched square brackets"

    # Check for unmatched curly braces
    if query.count('{') != query.count('}'):
        return True, "Unmatched curly braces"

    # Check query starts with valid Cypher keyword
    valid_starts = [
        'MATCH', 'CREATE', 'MERGE', 'RETURN',
        'WITH', 'CALL', 'UNWIND', 'OPTIONAL'
    ]
    first_word = query.upper().split()[0] if query.split() else ''
    if first_word not in valid_starts:
        return True, f"Does not start with valid keyword: {first_word}"

    # Check RETURN or action clause exists
    upper_query = query.upper()
    if 'RETURN' not in upper_query and 'DELETE' not in upper_query and \
       'SET' not in upper_query and 'CREATE' not in upper_query and \
       'MERGE' not in upper_query:
        return True, "Missing RETURN or action clause"

    # Check for unclosed string literals
    # Remove content inside strings first to handle apostrophes in names
    clean_query = query.replace("\\'", "").replace('\\"', "")
    clean_query = re.sub(r'"[^"]*"', '""', clean_query)
    clean_query = re.sub(r"'[^']*'", "''", clean_query)
    if clean_query.count("'") % 2 != 0:
        return True, "Unclosed single quote string"
    if clean_query.count('"') % 2 != 0:
        return True, "Unclosed double quote string"

    return False, ""

def run_syntax_classifier():
    df = pd.read_csv("data/generated_queries.csv")
    df['generated_cypher'] = df['generated_cypher'].fillna('')
    df['error'] = df['error'].fillna('')

    if 'syntax_error' not in df.columns:
        df['syntax_error'] = 0
    if 'syntax_error_msg' not in df.columns:
        df['syntax_error_msg'] = ''

    print("Running syntax classifier on 200 queries...")
    print("="*50)

    syntax_count = 0

    for i, row in df.iterrows():
        query = row['generated_cypher']

        if not query or query.strip() == '':
            df.at[i, 'syntax_error'] = 0
            continue

        is_error, msg = check_syntax(query)

        if is_error:
            df.at[i, 'syntax_error'] = 1
            df.at[i, 'syntax_error_msg'] = msg
            syntax_count += 1
            print(f"[{i+1}] SYNTAX ERROR — {msg}")
            print(f"     Q: {row['question'][:60]}...")
        else:
            df.at[i, 'syntax_error'] = 0
            df.at[i, 'syntax_error_msg'] = ''

    df.to_csv("data/generated_queries.csv", index=False)

    print("="*50)
    print(f"Syntax errors found: {syntax_count}/200")
    print(f"Clean queries: {200 - syntax_count}/200")
    print("Results saved to data/generated_queries.csv")

if __name__ == "__main__":
    run_syntax_classifier()