import pandas as pd
import time
import os
from google import genai
from dotenv import load_dotenv
from sacrebleu.metrics import BLEU

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Load progress if it exists, otherwise start fresh
if os.path.exists("data/generated_queries.csv"):
    df = pd.read_csv("data/generated_queries.csv")
    df['error'] = df['error'].fillna('').astype(str)
    df['generated_cypher'] = df['generated_cypher'].fillna('')
    print("Resuming from saved progress...")
else:
    df = pd.read_csv("data/sample_200.csv")
    df['generated_cypher'] = ''
    df['exact_match'] = 0
    df['bleu_score'] = 0.0
    df['error'] = ''
    print("Starting fresh...")

bleu = BLEU(effective_order=True)

# Only process rows with no result yet or had errors
pending = df[
    (df['generated_cypher'] == '') |
    (df['generated_cypher'].isna()) |
    (df['error'] != '')
].index.tolist()

print(f"Rows already done: {200 - len(pending)}")
print(f"Rows remaining: {len(pending)}")
print("="*50)

for count, i in enumerate(pending):
    row = df.loc[i]
    question = row['question']
    schema = row['schema']
    reference_cypher = row['cypher']

    df.at[i, 'error'] = ''

    prompt = f"""You are a Cypher query expert. Given the 
following graph schema and natural language question, 
generate a valid Cypher query.

Schema: {schema}
Question: {question}

Return only the Cypher query, nothing else."""

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt
        )
        generated = response.text.strip()

        if generated.startswith("```"):
            generated = generated.split("\n", 1)[1]
            generated = generated.rsplit("```", 1)[0].strip()

        df.at[i, 'generated_cypher'] = generated

        exact = 1 if generated.lower().strip() == \
                     reference_cypher.lower().strip() else 0
        df.at[i, 'exact_match'] = exact

        score = bleu.sentence_score(
            generated,
            [reference_cypher]
        ).score
        df.at[i, 'bleu_score'] = round(score, 4)

        print(f"[{count+1}/{len(pending)}] ✓ "
              f"BLEU: {round(score,2)} | "
              f"EM: {exact} | {question[:50]}...")

    except Exception as e:
        error_msg = str(e)[:200]
        df.at[i, 'error'] = error_msg
        print(f"[{count+1}/{len(pending)}] ✗ ERROR: "
              f"{error_msg[:80]}")

        if '429' in error_msg:
            print("Rate limit hit. Waiting 120 seconds...")
            df.to_csv("data/generated_queries.csv", index=False)
            time.sleep(120)
        elif '503' in error_msg:
            print("Server busy. Waiting 15 seconds...")
            time.sleep(15)

    time.sleep(5)

    if (count + 1) % 10 == 0:
        df.to_csv("data/generated_queries.csv", index=False)
        print(f"--- Progress saved at row {count+1} ---")

# Final save
df.to_csv("data/generated_queries.csv", index=False)
done = df[
    (df['generated_cypher'] != '') &
    (df['error'] == '')
].shape[0]
print("="*50)
print(f"Total complete: {done}/200")
print(f"Remaining: {200 - done}/200")
average_bleu = df[df['bleu_score'] > 0]['bleu_score'].mean()
print(f"Average BLEU score: {round(average_bleu, 4)}")
print(f"Exact Match count: {df['exact_match'].sum()}/200")