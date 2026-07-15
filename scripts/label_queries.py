import pandas as pd
import json
import os

df = pd.read_csv("data/generated_queries.csv")
df['error'] = df['error'].fillna('').astype(str)
df['generated_cypher'] = df['generated_cypher'].fillna('')

# Add label column if it doesn't exist
if 'manual_label' not in df.columns:
    df['manual_label'] = ''
if 'label_notes' not in df.columns:
    df['label_notes'] = ''

# Valid labels
LABELS = {
    '1': 'syntax_error',
    '2': 'schema_hallucination', 
    '3': 'logical_error',
    '4': 'performance_issue',
    '5': 'no_error',
    '6': 'multiple_errors'
}

# Only show unlabelled rows
pending = df[df['manual_label'] == ''].index.tolist()
already_done = df[df['manual_label'] != ''].shape[0]

print(f"Already labelled: {already_done}/40")
print(f"Remaining to label: {len(pending)}")
print("="*60)
print("Labels: 1=syntax  2=schema_hallucination  3=logical")
print("        4=performance  5=no_error  6=multiple_errors")
print("Type 'q' to quit and save progress")
print("="*60)

for i in pending[:40]:
    row = df.loc[i]
    
    print(f"\n--- Query {i+1}/200 ---")
    print(f"Complexity: {row.get('complexity', 'unknown')}")
    print(f"\nQUESTION:\n{row['question']}")
    print(f"\nSCHEMA:\n{row['schema'][:300]}...")
    print(f"\nREFERENCE CYPHER:\n{row['cypher']}")
    print(f"\nGENERATED CYPHER:\n{row['generated_cypher']}")
    print(f"\nBLEU: {row['bleu_score']} | Exact Match: {row['exact_match']}")
    print("\n1=syntax  2=schema_hallucination  3=logical")
    print("4=performance  5=no_error  6=multiple_errors")
    
    while True:
        choice = input("\nYour label: ").strip().lower()
        
        if choice == 'q':
            df.to_csv("data/generated_queries.csv", index=False)
            print(f"\nProgress saved. {df[df['manual_label'] != ''].shape[0]} queries labelled.")
            exit()
        
        if choice in LABELS:
            df.at[i, 'manual_label'] = LABELS[choice]
            notes = input("Notes (optional, press Enter to skip): ").strip()
            df.at[i, 'label_notes'] = notes
            print(f"✓ Labelled as: {LABELS[choice]}")
            break
        else:
            print("Invalid choice. Enter 1-6 or q to quit.")
    
    # Save every 5 queries
    if (df[df['manual_label'] != ''].shape[0]) % 5 == 0:
        df.to_csv("data/generated_queries.csv", index=False)
        print("--- Progress saved ---")

# Final save
df.to_csv("data/generated_queries.csv", index=False)
done = df[df['manual_label'] != ''].shape[0]
print(f"\n{'='*60}")
print(f"Session complete. Total labelled: {done}/40")
print(f"{'='*60}")