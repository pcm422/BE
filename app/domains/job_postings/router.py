from typing import List

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.utils import get_current_company_user
from app.domains.job_postings import service
from app.domains.job_postings.schemas import (JobPostingCreate,
                                              JobPostingResponse,
                                              JobPostingUpdate)
from app.models.company_users import CompanyUser

router = APIRouter(prefix="/posting", tags=["채용공고"])


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
    response_model=List[JobPostingResponse],
    summary="채용공고 전체 목록 조회",
    description="모든 채용공고를 조회합니다.",
)
async def list_postings(session: AsyncSession = Depends(get_db_session)):
    return await service.list_job_postings(session)


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
    posting = await service.get_job_posting(session, job_posting_id)
    if not posting:
        raise HTTPException(status_code=404, detail="수정할 채용공고가 없습니다.")
    if posting.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="본인 공고만 수정할 수 있습니다.")

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
    posting = await service.get_job_posting(session, job_posting_id)
    if not posting:
        raise HTTPException(status_code=404, detail="삭제할 채용공고가 없습니다.")
    if posting.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="본인 공고만 삭제할 수 있습니다.")

    await service.delete_job_posting(session, job_posting_id)
    return None
