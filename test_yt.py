import httpx
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

async def test_youtube_api():
    api_key = os.getenv("YOUTUBE_DATA_API_KEY")
    query = "Electric Charge"
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "maxResults": 3,
        "type": "video",
        "key": api_key
    }
    
    print(f"Testing YouTube API with key: {api_key}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Success!")
                print(response.json())
            else:
                print("Failure details:")
                print(response.text)
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_youtube_api())
