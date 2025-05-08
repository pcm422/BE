from fastapi import APIRouter

from .service import summary_jobposting
from .schemas import AIJobPostSchema,SummarizeResponse
from ..company_users.schemas import SuccessResponse
from ..company_users.utiles import success_response

router = APIRouter(prefix="/ai", tags=["ai 공고 요약"])

@router.post("/summarize",
            response_model=SuccessResponse[SummarizeResponse],
            summary="공고 요약 요청",
            description="구인 공고 정보를 전달하면 CLOVA AI를 통해 요약문을 생성합니다.")
async def ai_summarize(job:AIJobPostSchema):
    summary = await summary_jobposting(job)
    return success_response(
        message="공고 요약이 완료 되었습니다.",
        data={"summary": summary}
    )