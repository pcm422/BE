from fastapi import APIRouter, Body, HTTPException

from .service import summary_jobposting
from .schemas import AIJobPostSchema,SummarizeResponse

router = APIRouter()

@router.post("/posting/ai-summary",
            tags=["AI 공고요약"],
            response_model=SummarizeResponse)
async def ai_summarize(request: AIJobPostSchema = Body(...)):
    summary = await summary_jobposting(request.content)
    if not request.content.strip():
        raise HTTPException(400, "content가 비어있습니다.")
    return SummarizeResponse(summary=summary)