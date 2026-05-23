import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

try:
    llm = ChatOpenAI(
        model="google/gemma-4-26b-a4b-it",
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=4000,
        default_headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://gemminate.com", 
            "X-Title": "Gemminate"
        }
    )
    res = llm.invoke([HumanMessage(content="Hello")])
    print("WITH HEADERS:", res.content)
except Exception as e:
    print("ERROR WITH HEADERS:", e)

try:
    llm2 = ChatOpenAI(
        model="google/gemma-4-26b-a4b-it",
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=4000
    )
    res = llm2.invoke([HumanMessage(content="Hello")])
    print("WITHOUT HEADERS:", res.content)
except Exception as e:
    print("ERROR WITHOUT HEADERS:", e)
