import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "google/gemini-embedding-2-preview",
    "input": ["Hello world"],
    "encoding_format": "base64"
}

response = requests.post("https://openrouter.ai/api/v1/embeddings", headers=headers, json=data)
print("Status:", response.status_code)
print("Response:", response.text)
