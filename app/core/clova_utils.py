import os
import httpx

CLOVA_API_URL = os.getenv("CLOVA_API_URL")
CLOVA_API_KEY = os.getenv("CLOVA_API_KEY")

async def call_clova(messages: list[dict]) -> str:
    if not CLOVA_API_URL or not CLOVA_API_KEY:
        raise RuntimeError(f"API 키가 올바르지 않습니다.")
    headers = {
        "Authorization": f"Bearer {CLOVA_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(CLOVA_API_URL,headers=headers,json={"messages": messages})
        response.raise_for_status()
        return response.json()["result"]["message"]["content"]