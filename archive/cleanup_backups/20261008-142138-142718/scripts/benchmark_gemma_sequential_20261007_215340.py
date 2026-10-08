"""
Generate Gemma answers for the existing 200-question sample.

Run:
    python scripts/benchmark_gemma.py

Run the same command again to resume interrupted progress.
Original Gemini results are never modified.
"""

import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google import genai
from sacrebleu.metrics import BLEU

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "data/generated_queries.csv"
OUTPUT = PROJECT / "outputs/benchmark_gemma.csv"

MODEL = "gemma-4-31b-it"
PAUSE_SECONDS = 5
MAX_ATTEMPTS = 4

load_dotenv(PROJECT / ".env")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("GEMINI_API_KEY was not found in .env.")

source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
source = pd.read_csv(SOURCE, keep_default_na=False)

required = {"instance_id", "question", "schema", "cypher"}
missing = required - set(source.columns)
if missing:
    raise SystemExit(f"Source columns missing: {sorted(missing)}")

if len(source) != 200:
    raise SystemExit(f"Expected 200 records; found {len(source)}.")

if source["instance_id"].eq("").any() or source["instance_id"].duplicated().any():
    raise SystemExit("Source IDs must be present and unique.")

# Copy input material only, without historical classifier labels.
columns = [
    column for column in (
        "instance_id", "question", "schema", "cypher",
        "complexity", "data_source", "database_reference_alias"
    )
    if column in source.columns
]

if OUTPUT.exists():
    results = pd.read_csv(OUTPUT, keep_default_na=False)

    if results["instance_id"].duplicated().any():
        raise SystemExit("Duplicate IDs in saved benchmark.")

    if set(results["instance_id"]) != set(source["instance_id"]):
        raise SystemExit("Saved benchmark IDs do not match the source.")

    if not results["source_sha256"].eq(source_hash).all():
        raise SystemExit(
            "Source file changed since this benchmark started. "
            "Existing progress was not modified."
        )

    if not results["model_requested"].eq(MODEL).all():
        raise SystemExit("Saved benchmark uses a different model.")

    results = (
        results.set_index("instance_id")
        .loc[source["instance_id"]]
        .reset_index()
    )
    print("Resuming saved benchmark.", flush=True)

else:
    results = source[columns].copy()

    defaults = {
        "model_requested": MODEL,
        "model_reported": "",
        "source_sha256": source_hash,
        "prompt_sha256": "",
        "generation_settings": "provider_defaults_not_explicitly_set",
        "generated_cypher": "",
        "raw_response": "",
        "generation_status": "pending",
        "finish_reason": "",
        "generated_at_utc": "",
        "elapsed_seconds": "",
        "input_tokens": "",
        "output_tokens": "",
        "total_tokens": "",
        "bleu_score": "",
        "historical_lowercase_exact_match": "",
        "case_sensitive_trimmed_exact_match": "",
        "generation_error": "",
    }

    for column, value in defaults.items():
        results[column] = value

    print("Starting a separate Gemma benchmark.", flush=True)

# Allow numeric measurements in initially blank CSV columns.
results = results.astype(object)

bleu = BLEU(effective_order=True)


def save_progress():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp")
    results.to_csv(temporary, index=False)
    temporary.replace(OUTPUT)


def clean_query(text):
    """Apply the same surrounding code-fence cleanup as the original script."""
    text = text.strip()

    if text.startswith("```") and "\n" in text:
        text = text.split("\n", 1)[1]
        if "```" in text:
            text = text.rsplit("```", 1)[0]
        text = text.strip()

    return text


pending = results.index[
    results["generation_status"].ne("completed")
].tolist()

print(f"Completed: {len(results) - len(pending)}/200", flush=True)
print(f"Remaining: {len(pending)}", flush=True)
print(f"Each request is followed by a {PAUSE_SECONDS}-second pause.", flush=True)

save_progress()
client = genai.Client(api_key=api_key)

try:
    for position, index in enumerate(pending, start=1):
        row = results.loc[index]

        # Original prompt wording; reference query is not sent.
        prompt = f"""You are a Cypher query expert. Given the 
following graph schema and natural language question, 
generate a valid Cypher query.

Schema: {row['schema']}
Question: {row['question']}

Return only the Cypher query, nothing else."""

        results.at[index, "prompt_sha256"] = hashlib.sha256(
            prompt.encode("utf-8")
        ).hexdigest()

        results.at[index, "generation_error"] = ""

        for attempt in range(1, MAX_ATTEMPTS + 1):
            started = time.perf_counter()

            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                )

                raw_text = (response.text or "").strip()
                candidates = response.candidates or []
                reason = (
                    getattr(candidates[0].finish_reason, "value",
                            str(candidates[0].finish_reason))
                    if candidates else ""
                )

                results.at[index, "raw_response"] = raw_text
                results.at[index, "finish_reason"] = reason
                results.at[index, "model_reported"] = (
                    getattr(response, "model_version", "") or ""
                )
                results.at[index, "generated_at_utc"] = (
                    datetime.now(timezone.utc).isoformat()
                )
                results.at[index, "elapsed_seconds"] = round(
                    time.perf_counter() - started, 3
                )

                usage = response.usage_metadata
                if usage:
                    for column, attribute in (
                        ("input_tokens", "prompt_token_count"),
                        ("output_tokens", "candidates_token_count"),
                        ("total_tokens", "total_token_count"),
                    ):
                        value = getattr(usage, attribute, None)
                        results.at[index, column] = (
                            value if value is not None else ""
                        )

                query = clean_query(raw_text)

                if not query or reason not in ("STOP", "FinishReason.STOP"):
                    results.at[index, "generation_status"] = "needs_review"
                    results.at[index, "generation_error"] = (
                        f"Empty or unfinished response; finish_reason={reason}"
                    )
                    break

                reference = str(row["cypher"]).strip()

                results.at[index, "generated_cypher"] = query
                results.at[index, "bleu_score"] = round(
                    bleu.sentence_score(query, [reference]).score, 4
                )
                results.at[index, "historical_lowercase_exact_match"] = int(
                    query.lower().strip() == reference.lower()
                )
                results.at[index, "case_sensitive_trimmed_exact_match"] = int(
                    query.strip() == reference
                )
                results.at[index, "generation_status"] = "completed"
                results.at[index, "generation_error"] = ""
                break

            except Exception as error:
                message = str(error).replace(api_key, "[API key hidden]")
                results.at[index, "generation_status"] = "failed"
                results.at[index, "generation_error"] = message[:1200]
                save_progress()

                code = str(getattr(error, "code", ""))
                retryable = code in {"429", "500", "502", "503", "504"}

                if not retryable or attempt == MAX_ATTEMPTS:
                    print(
                        f"Request failed: {type(error).__name__}: "
                        f"{message[:250]}",
                        flush=True,
                    )
                    break

                wait_seconds = 30 * attempt
                print(
                    f"API error {code}: {message[:250]}. "
                    f"Retrying in {wait_seconds} seconds "
                    f"({attempt}/{MAX_ATTEMPTS}).",
                    flush=True,
                )
                time.sleep(wait_seconds)

        save_progress()

        print(
            f"[{position}/{len(pending)}] {row['instance_id']}: "
            f"{results.at[index, 'generation_status']}",
            flush=True,
        )

        # Stop rather than repeat an account/access error 200 times.
        error_text = str(results.at[index, "generation_error"]).lower()
        if results.at[index, "generation_status"] == "failed" and any(
            term in error_text
            for term in ("prepayment", "billing", "api key not valid",
                         "permission_denied", "unauthenticated")
        ):
            print("Account/access problem detected. Progress saved.", flush=True)
            break

        if position < len(pending):
            time.sleep(PAUSE_SECONDS)

except KeyboardInterrupt:
    print("\nInterrupted. Progress saved; rerun to resume.", flush=True)

finally:
    save_progress()
    client.close()

completed = results["generation_status"].eq("completed")
print("\nGENERATION SUMMARY")
print(results["generation_status"].value_counts().to_string())
print(f"Completed: {int(completed.sum())}/200")

if completed.any():
    scores = pd.to_numeric(
        results.loc[completed, "bleu_score"], errors="coerce"
    )
    print(f"Mean sentence BLEU: {scores.mean():.4f}")

print(f"Saved: {OUTPUT}")
print("Original Gemini results were not changed.")
print("Syntax, schema and database evaluation are still required.")
