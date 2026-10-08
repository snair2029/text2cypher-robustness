import pandas as pd

df = pd.read_csv("text2cypher_full.csv")

# How many unique data sources are there?
print("=== Data Sources ===")
print(df['data_source'].value_counts())

print("\n=== Sample questions by complexity ===")

# Short questions (simple)
short = df[df['question'].str.len() < 50]
print(f"\nShort/simple questions (under 50 chars): {len(short)}")
print(short['question'].head(3).tolist())

# Medium questions
medium = df[(df['question'].str.len() >= 50) & 
            (df['question'].str.len() < 100)]
print(f"\nMedium questions (50-100 chars): {len(medium)}")
print(medium['question'].head(3).tolist())

# Long/complex questions
long = df[df['question'].str.len() >= 100]
print(f"\nLong/complex questions (100+ chars): {len(long)}")
print(long['question'].head(3).tolist())

# Cypher complexity - count keywords
df['cypher_complexity'] = df['cypher'].str.count(
    'WHERE|WITH|MATCH|OPTIONAL|UNION|LIMIT|ORDER|GROUP'
)
print("\n=== Cypher complexity distribution ===")
print(df['cypher_complexity'].value_counts().head(10))