from datasets import load_dataset
import pandas as pd

print("Downloading dataset...")
dataset = load_dataset("neo4j/text2cypher-2024v1", split="train")
df = dataset.to_pandas()

print(f"Total rows: {df.shape[0]}")
print(f"Columns: {df.columns.tolist()}")
print(df.head(3))

df.to_csv("text2cypher_full.csv", index=False)
print("Saved to text2cypher_full.csv")
