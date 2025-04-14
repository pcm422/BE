from fastapi import APIRouter, Depends, Query, status
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.utils import get_current_company_user
from app.domains.job_postings import service
from app.domains.job_postings.schemas import (JobPostingCreate,
                                              JobPostingResponse,
                                              JobPostingUpdate,
                                              PaginatedJobPostingResponse)
from app.models.company_users import CompanyUser
from app.models.job_postings import JobPosting

router = APIRouter(prefix="/posting", tags=["채용공고"])


async def get_posting_with_permission_check(
    job_posting_id: int,
    session: AsyncSession,
    current_user: CompanyUser,
    action_type: str = "수정"
) -> JobPosting:
    """
    게시물을 조회하고 권한을 확인하는 공통 함수
    
    Args:
        job_posting_id: 채용공고 ID
        session: DB 세션
        current_user: 현재 로그인한 사용자
        action_type: 작업 타입(수정, 삭제 등)
        
    Returns:
        채용공고 객체
        
    Raises:
        HTTPException: 게시물이 존재하지 않거나 권한이 없는 경우
    """
    posting = await service.get_job_posting(session, job_posting_id)
    if not posting:
        raise HTTPException(status_code=404, detail=f"{action_type}할 채용공고가 없습니다.")
    if posting.author_id != current_user.id:
        raise HTTPException(status_code=403, detail=f"본인 공고만 {action_type}할 수 있습니다.")
    return posting


@router.post(
    "/",
    response_model=JobPostingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="채용공고 생성",
    description="로그인된 기업 담당자가 새로운 채용공고를 등록합니다.",
)
async def create_job_posting(
    data: JobPostingCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
):
    return await service.create_job_posting(
        session=session,
        data=data,
        author_id=current_user.id,
        company_id=current_user.company_id,
    )


@router.get(
    "/",
    response_model=PaginatedJobPostingResponse,
    summary="채용공고 목록 조회",
    description="채용공고 목록을 페이지네이션하여 조회합니다.",
)
async def list_postings(
    skip: int = Query(0, ge=0, description="건너뛸 레코드 수"),
    limit: int = Query(10, ge=1, le=100, description="가져올 레코드 수"),
    session: AsyncSession = Depends(get_db_session)
):
    postings, total_count = await service.list_job_postings(
        session=session, skip=skip, limit=limit
    )
    
    # SQLAlchemy 모델을 Pydantic 모델로 변환 (Pydantic v2)
    posting_responses = [JobPostingResponse.model_validate(posting) for posting in postings]
    
    return {
        "items": posting_responses,
        "total": total_count,
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "/{job_posting_id}",
    response_model=JobPostingResponse,
    summary="채용공고 상세 조회",
    description="특정 채용공고의 상세정보를 조회합니다.",
)
async def get_posting(
    job_posting_id: int, session: AsyncSession = Depends(get_db_session)
):
    posting = await service.get_job_posting(session, job_posting_id)
    if not posting:
        raise HTTPException(status_code=404, detail="채용공고를 찾을 수 없습니다.")
    return posting


@router.patch(
    "/{job_posting_id}",
    response_model=JobPostingResponse,
    summary="채용공고 수정",
    description="로그인된 기업 담당자가 자신이 올린 채용공고를 수정합니다.",
)
async def update_posting(
    job_posting_id: int,
    data: JobPostingUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
):
    posting = await get_posting_with_permission_check(
        job_posting_id=job_posting_id,
        session=session,
        current_user=current_user,
        action_type="수정"
    )
    return await service.update_job_posting(session, job_posting_id, data)


@router.delete(
    "/{job_posting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="채용공고 삭제",
    description="로그인된 기업 담당자가 자신이 올린 채용공고를 삭제합니다.",
)
async def delete_posting(
    job_posting_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
):
    posting = await get_posting_with_permission_check(
        job_posting_id=job_posting_id,
        session=session,
        current_user=current_user,
        action_type="삭제"
    )
    await service.delete_job_posting(session, job_posting_id)
    return None