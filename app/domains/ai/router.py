from fastapi import APIRouter, Body, HTTPException

from .service import summary_jobposting
from .schemas import AIJobPostSchema,SummarizeResponse

router = APIRouter(prefix="/ai", tags=["ai 공고 요약"])

@router.post("/summary",
            response_model=SummarizeResponse)
async def ai_summarize(request: AIJobPostSchema = Body(...)):
    summary = await summary_jobposting(request.content)
    if not request.content.strip():
        raise HTTPException(400, "content가 비어있습니다.")
    return SummarizeResponse(summary=summary)