from typing import Any
from enum import Enum

from fastapi import APIRouter, Depends, Query, status, UploadFile, File
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.utils import get_current_company_user
from app.domains.job_postings import service
from app.domains.job_postings.schemas import (
                                              JobPostingResponse,
                                              JobPostingUpdate,
                                              PaginatedJobPostingResponse,
                                              JobPostingCreateFormData)
from app.models.company_users import CompanyUser
from app.models.job_postings import JobPosting, JobCategoryEnum

# SortOptions Enum 클래스 추가
class SortOptions(str, Enum):
    LATEST = "latest"
    DEADLINE = "deadline"
    SALARY_HIGH = "salary_high"
    SALARY_LOW = "salary_low"

router = APIRouter(prefix="/posting", tags=["채용공고"])


async def get_posting_or_404(
    session: AsyncSession, job_posting_id: int
) -> JobPosting:
    """ID로 채용공고를 조회하고 없으면 404 에러 발생"""
    posting = await service.get_job_posting(session, job_posting_id)
    if not posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채용공고를 찾을 수 없습니다.")
    return posting


async def check_posting_permission(
    posting: JobPosting, current_user: CompanyUser, action_type: str = "접근"
):
    """채용공고에 대한 현재 사용자의 권한 확인"""
    # 작성자만 수정/삭제 가능
    if posting.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"본인 공고만 {action_type}할 수 있습니다.")


@router.post(
    "/",
    response_model=JobPostingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="채용공고 생성",
    description="로그인된 기업 담당자가 새로운 채용공고를 등록합니다. 이미지 파일을 함께 업로드할 수 있습니다.",
)
async def create_job_posting(
    form_data: JobPostingCreateFormData = Depends(),
    image_file: UploadFile = File(None, description="채용공고 이미지 파일 (선택사항)"),
    session: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
) -> JobPosting:
    """채용공고 생성 API"""
    try:
        # 1. Form 데이터를 JobPostingCreate Pydantic 모델로 변환 및 유효성 검사
        # 이미지 URL은 이 단계에서는 None 또는 빈 값으로 두고, 서비스에서 처리
        job_posting_create_data = form_data.parse_to_job_posting_create(postings_image_url=None)

        # 2. 서비스 호출하여 공고 생성
        created_posting = await service.create_job_posting(
            session=session,
            job_posting_data=job_posting_create_data, # 변환된 Pydantic 모델 전달
            author_id=current_user.id,
            company_id=current_user.company_id,
            image_file=image_file, # 이미지 파일 전달
        )
        # 서비스에서 성공 시 ORM 객체 반환
        return created_posting
    except HTTPException as http_exc:
        # 스키마 변환 또는 서비스 로직에서 발생한 HTTP 예외 재발생
        raise http_exc
    except Exception as e:
        # 기타 예상치 못한 오류 처리
        print(f"Error: 채용 공고 생성 라우터 오류 - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"채용 공고 생성 중 서버 오류 발생: {e}"
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
) -> PaginatedJobPostingResponse:
    """채용공고 목록 조회 API"""
    postings, total_count = await service.list_job_postings(
        session=session, skip=skip, limit=limit
    )

    # response_model에 맞춰 Pydantic 모델 객체 반환
    return PaginatedJobPostingResponse(
        items=postings,
        total=total_count,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/search",
    response_model=PaginatedJobPostingResponse,
    summary="채용공고 검색",
    description="키워드 및 필터 기반으로 채용공고를 검색합니다.",
)
async def search_postings(
    keyword: str | None = Query(None, description="검색 키워드 (제목, 내용에서 검색)"),
    location: str | None = Query(None, description="근무지 위치"),
    job_category: JobCategoryEnum | None = Query(None, description="직무 카테고리"),
    employment_type: str | None = Query(None, description="고용 형태"),
    is_always_recruiting: bool | None = Query(None, description="상시 채용 여부"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(10, ge=1, le=100, description="페이지당 결과 수"),
    sort: SortOptions = Query(SortOptions.LATEST, description="정렬 기준"),
    session: AsyncSession = Depends(get_db_session)
) -> PaginatedJobPostingResponse:
    """채용공고 검색 API"""
    postings, total_count = await service.search_job_postings(
        session=session,
        keyword=keyword,
        location=location,
        job_category=job_category.value if job_category else None,
        employment_type=employment_type,
        is_always_recruiting=is_always_recruiting,
        page=page,
        limit=limit,
        sort=sort.value
    )

    return PaginatedJobPostingResponse(
        items=postings,
        total=total_count,
        skip=(page - 1) * limit,
        limit=limit,
    )


@router.get(
    "/popular",
    response_model=PaginatedJobPostingResponse,
    summary="인기 채용공고 목록 조회",
    description="지원자 수가 많은 인기 채용공고를 조회합니다.",
)
async def list_popular_postings(
    limit: int = Query(10, ge=1, le=100, description="가져올 레코드 수"),
    session: AsyncSession = Depends(get_db_session)
) -> PaginatedJobPostingResponse:
    """인기 채용공고 목록 조회 API"""
    postings, total_count = await service.get_popular_job_postings(
        session=session, limit=limit
    )

    # 인기 목록 조회는 total 개수가 전체 공고 수이므로 약간 의미가 다를 수 있음
    # 프론트엔드와 협의하여 total을 반환할지 결정 필요
    return PaginatedJobPostingResponse(
        items=postings,
        total=total_count,
        skip=0,
        limit=limit,
    )


@router.get(
    "/{job_posting_id}",
    response_model=JobPostingResponse,
    summary="채용공고 상세 조회",
    description="특정 채용공고의 상세정보를 조회합니다.",
)
async def get_posting(
    job_posting_id: int, session: AsyncSession = Depends(get_db_session)
) -> JobPosting:
    """채용공고 상세 조회 API"""
    posting = await get_posting_or_404(session, job_posting_id)
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
) -> JobPosting:
    """채용공고 수정 API"""
    posting = await get_posting_or_404(session, job_posting_id)

    await check_posting_permission(posting, current_user, action_type="수정")

    updated_posting = await service.update_job_posting(
        session=session, job_posting_id=job_posting_id, data=data
    )
    if updated_posting is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="공고 업데이트 처리 중 오류 발생")

    return updated_posting


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
) -> None:
    """채용공고 삭제 API"""
    posting = await get_posting_or_404(session, job_posting_id)

    await check_posting_permission(posting, current_user, action_type="삭제")

    deleted_posting = await service.delete_job_posting(session=session, job_posting_id=job_posting_id)

    if deleted_posting is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="공고 삭제 처리 중 오류 발생")

    return None