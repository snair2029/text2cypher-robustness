from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

# Real sample from your dataset
question = "Which 3 countries have the most entities linked to them?"
schema = "(:Entity)-[:LOCATED_IN]->(:Country)"

prompt = f"""You are a Cypher query expert. Given the following 
graph schema and natural language question, generate a valid 
Cypher query.

Schema: {schema}
Question: {question}

Return only the Cypher query, nothing else."""

response = client.models.generate_content(
    model="gemini-2.5-flash-lite",
    contents=prompt
)

print("Generated Cypher:")
print(response.text)