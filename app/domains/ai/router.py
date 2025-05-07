from fastapi import APIRouter

from .service import summary_jobposting
from .schemas import AIJobPostSchema,SummarizeResponse

router = APIRouter(prefix="/ai", tags=["ai 공고 요약"])

@router.post("/summarize",
            response_model=SummarizeResponse)
async def ai_summarize(job:AIJobPostSchema):
    summary = await summary_jobposting(job)
    return SummarizeResponse(summary=summary)