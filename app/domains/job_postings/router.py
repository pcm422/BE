from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_company_user
from app.core.db import get_db_session
from app.domains.job_postings import service
from app.domains.job_postings.schemas import JobPostingCreate, JobPostingResponse
from app.models.company_users import CompanyUser

router = APIRouter(prefix="/posting", tags=["채용공고"])

@router.post(
    "/",
    response_model=JobPostingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="채용공고 생성",
    description="로그인된 기업 담당자가 새로운 채용공고를 등록합니다."
)
async def create_job_posting(
    data: JobPostingCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user)
):
    return await service.create_job_posting(
        session=session,
        data=data,
        author_id=current_user.id,
        company_id=current_user.company_id
    )
