import pandas as pd
import re

# ─────────────────────────────────────────
# SYNTAX CHECK
# ─────────────────────────────────────────


def check_syntax(query):
    """
    Apply rule-based checks to detect common Cypher syntax errors.
    Returns (is_error: bool, error_message: str)
    """
    if not query or query.strip() == "":
        return True, "Empty query"

    query = query.strip()

    # Check balanced brackets
    if query.count("(") != query.count(")"):
        return True, "Unmatched parentheses"

    if query.count("[") != query.count("]"):
        return True, "Unmatched square brackets"

    if query.count("{") != query.count("}"):
        return True, "Unmatched curly braces"

    # Check query begins with a valid Cypher keyword
    valid_starts = [
        "MATCH",
        "CREATE",
        "MERGE",
        "RETURN",
        "WITH",
        "CALL",
        "UNWIND",
        "OPTIONAL",
    ]
    first_word = query.upper().split()[0] if query.split() else ""
    if first_word not in valid_starts:
        return True, f"Invalid opening keyword: {first_word}"

    # Check a RETURN or action clause is present
    upper = query.upper()
    has_action = any(
        kw in upper for kw in ["RETURN", "DELETE", "SET", "CREATE", "MERGE"]
    )
    if not has_action:
        return True, "Missing RETURN or action clause"

    # Check for unclosed string literals
    # Strip string contents first to avoid counting apostrophes in names
    clean = query.replace("\\'", "").replace('\\"', "")
    clean = re.sub(r'"[^"]*"', '""', clean)
    clean = re.sub(r"'[^']*'", "''", clean)

    if clean.count("'") % 2 != 0:
        return True, "Unclosed single-quote string"
    if clean.count('"') % 2 != 0:
        return True, "Unclosed double-quote string"

    return False, ""


# ─────────────────────────────────────────
# MAIN CLASSIFIER
# ─────────────────────────────────────────


def run_syntax_classifier():
    df = pd.read_csv("data/generated_queries.csv")
    df["generated_cypher"] = df["generated_cypher"].fillna("").astype(str)

    if "syntax_error" not in df.columns:
        df["syntax_error"] = 0
    if "syntax_error_msg" not in df.columns:
        df["syntax_error_msg"] = ""

    df["syntax_error"] = df["syntax_error"].fillna(0).astype(int)
    df["syntax_error_msg"] = df["syntax_error_msg"].fillna("").astype(str)

    print("Syntax Error Classifier")
    print("=" * 50)

    syntax_count = 0

    for i, row in df.iterrows():
        query = row["generated_cypher"]

        if not query or query.strip() == "":
            df.at[i, "syntax_error"] = 0
            continue

        is_error, msg = check_syntax(query)

        df.at[i, "syntax_error"] = 1 if is_error else 0
        df.at[i, "syntax_error_msg"] = msg if is_error else ""

        if is_error:
            syntax_count += 1
            print(f"[{i+1}] SYNTAX ERROR | {msg}")
            print(f"      {row['question'][:70]}")

    df.to_csv("data/generated_queries.csv", index=False)

    print("=" * 50)
    print(f"Syntax errors    : {syntax_count} / 200")
    print(f"Clean queries    : {200 - syntax_count} / 200")
    print("Saved → data/generated_queries.csv")


if __name__ == "__main__":
    run_syntax_classifier()
