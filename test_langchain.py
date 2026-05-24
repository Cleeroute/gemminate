import os
import logging
from dotenv import load_dotenv
load_dotenv()

import httpx

import traceback

from langchain_openai import OpenAIEmbeddings

api_key = os.getenv("OPENROUTER_API_KEY")

import httpx
client = httpx.Client(
    event_hooks={'request': [lambda request: print(f"REQ: {request.content}")]}
)

embeddings_model = OpenAIEmbeddings(
    model="google/gemini-embedding-2-preview",
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    check_embedding_ctx_length=False,
    model_kwargs={"encoding_format": "float"},
    http_client=client
)

try:
    docs = ["Hello world", "This is a test"]
    res = embeddings_model.embed_documents(docs)
    print("Success! Number of embeddings:", len(res))
except Exception as e:
    print("Error:", e)
