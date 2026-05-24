from dotenv import load_dotenv
load_dotenv()
import os
from langchain_openai import OpenAIEmbeddings

api_key = os.getenv("OPENROUTER_API_KEY")

embeddings_model = OpenAIEmbeddings(
    model="google/gemini-embedding-2-preview",
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

try:
    res = embeddings_model.embed_query("Hello world")
    print("Success! Dimensions:", len(res))
except Exception as e:
    print("Error:", e)
