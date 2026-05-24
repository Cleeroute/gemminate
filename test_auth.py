import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

def test_key(key):
    try:
        llm = ChatOpenAI(
            model="google/gemma-4-26b-a4b-it",
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
            max_tokens=4000
        )
        res = llm.invoke([HumanMessage(content="Hello")])
        print(f"Key '{key}': Success")
    except Exception as e:
        print(f"Key '{key}': ERROR: {e}")

test_key("invalid_key")
test_key(" ")
test_key("")
