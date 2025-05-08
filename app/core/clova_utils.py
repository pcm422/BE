
import httpx
from fastapi import HTTPException ,status

from app.core.config import CLOVA_API_URL, CLOVA_API_KEY


async def call_clova_summary(messages: list[dict]) -> str:
    if not CLOVA_API_URL or not CLOVA_API_KEY:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLOVA API 설정이 잘못되었습니다. 관리자에게 문의하세요."
        )
    headers = {
        "Authorization": f"Bearer {CLOVA_API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }
    request_data = {
        "messages": messages,
        "topP": 0.8,
        "topK": 0,
        "maxTokens": 256,
        "temperature": 0.3,
        "repeatPenalty": 1.2,
        "stopBefore": [],
        "includeAiFilters": True,
        "seed": 0
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(CLOVA_API_URL,headers=headers,json=request_data)
            response.raise_for_status()
            data = response.json()
            result = data.get("result", {}).get("message", {}).get("content", "")
            if not result:
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    detail="요약 결과가 비어 있습니다. 다시 시도해주세요."
                )
            return result

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"CLOVA 응답 오류 : {e.response.text}"
        )

    except httpx.RequestError as e:
        raise HTTPException(
            status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"CLOVA 요청 실패 :{str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"요약 중 알 수 없는 오류 : {str(e)}"
        )