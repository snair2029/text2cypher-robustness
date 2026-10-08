import pandas as pd

df = pd.read_csv("text2cypher_full.csv")


# Define complexity based on question length
def complexity_level(question):
    length = len(question)
    if length < 50:
        return "simple"
    elif length < 100:
        return "medium"
    else:
        return "complex"


df["complexity"] = df["question"].apply(complexity_level)

# Also add cypher complexity score
df["cypher_complexity"] = df["cypher"].str.count(
    "WHERE|WITH|MATCH|OPTIONAL|UNION|LIMIT|ORDER|GROUP"
)

print("=== Complexity distribution ===")
print(df["complexity"].value_counts())

# Stratified sample - 200 total
# Simple: 50, Medium: 100, Complex: 50
simple_sample = df[df["complexity"] == "simple"].sample(n=50, random_state=42)
medium_sample = df[df["complexity"] == "medium"].sample(n=100, random_state=42)
complex_sample = df[df["complexity"] == "complex"].sample(n=50, random_state=42)

# Combine into final sample
sample_df = pd.concat([simple_sample, medium_sample, complex_sample]).reset_index(
    drop=True
)

print(f"\n=== Final sample ===")
print(f"Total rows: {len(sample_df)}")
print(f"Simple: {len(simple_sample)}")
print(f"Medium: {len(medium_sample)}")
print(f"Complex: {len(complex_sample)}")
print(f"\nComplexity distribution:")
print(sample_df["complexity"].value_counts())
print(f"\nData sources represented:")
print(sample_df["data_source"].value_counts())
print(f"\nSample questions:")
print(sample_df[["question", "complexity"]].head(6))

# Save to CSV
sample_df.to_csv("sample_200.csv", index=False)
print("\nSaved to sample_200.csv")
