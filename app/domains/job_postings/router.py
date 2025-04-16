from typing import Any, Optional
from enum import Enum

from fastapi import APIRouter, Depends, Query, status, Form, UploadFile, File
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.utils import get_current_company_user
from app.domains.job_postings import service
from app.domains.job_postings.schemas import (
                                              JobPostingResponse,
                                              JobPostingUpdate,
                                              PaginatedJobPostingResponse,
                                              JobPostingCreateWithImage)
from app.models.company_users import CompanyUser
from app.models.job_postings import JobPosting, JobCategoryEnum

# SortOptions Enum 클래스 추가
class SortOptions(str, Enum):
    LATEST = "latest"
    DEADLINE = "deadline"
    SALARY_HIGH = "salary_high"
    SALARY_LOW = "salary_low"

router = APIRouter(prefix="/posting", tags=["채용공고"])


async def get_posting_with_permission_check(
    job_posting_id: int,
    session: AsyncSession,
    current_user: CompanyUser,
    action_type: str = "접근"
) -> JobPosting:
    """
    채용공고를 조회하고 현재 사용자의 권한을 확인하는 공통 함수
    
    Args:
        job_posting_id: 채용공고 ID
        session: DB 세션
        current_user: 현재 로그인한 기업 사용자
        action_type: 수행하려는 작업 유형(에러 메시지에 사용)
        
    Returns:
        JobPosting: 권한이 확인된 채용공고 객체
        
    Raises:
        HTTPException: 채용공고가 없거나 권한이 없는 경우
    """
    posting = await service.get_job_posting(session, job_posting_id)
    if not posting:
        raise HTTPException(status_code=404, detail=f"{action_type}할 채용공고가 없습니다.")
    
    # 작성자만 수정/삭제 가능
    if posting.author_id != current_user.id:
        raise HTTPException(status_code=403, detail=f"본인 공고만 {action_type}할 수 있습니다.")
    
    return posting


@router.post(
    "/",
    response_model=JobPostingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="채용공고 생성",
    description="로그인된 기업 담당자가 새로운 채용공고를 등록합니다. 이미지 파일을 함께 업로드할 수 있습니다.",
)
async def create_job_posting(
    job_posting: JobPostingCreateWithImage = Depends(JobPostingCreateWithImage.as_form),
    image_file: UploadFile = File(None, description="채용공고 이미지 파일 (선택사항)"),
    session: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
) -> JobPostingResponse:
    """채용공고 생성 API
    
    Args:
        job_posting: 채용공고 생성 요청 데이터
        image_file: 첨부할 이미지 파일 (선택사항)
        session: DB 세션
        current_user: 현재 로그인한 기업 사용자
        
    Returns:
        생성된 채용공고 정보
    
    Example:
        ```
        # 폼 데이터로 전송:
        - title: "개발자 채용"
        - author_id: 1
        - company_id: 1
        - recruit_period_start: "2025-04-20"
        - recruit_period_end: "2025-05-20"
        - is_always_recruiting: false
        - education: "college_4"
        - recruit_number: "2"
        - work_address: "서울시 강남구"
        - work_place_name: "본사"
        - payment_method: "monthly"
        - job_category: "it"
        - work_duration: "more_1_year"
        - career: "경력 3년 이상"
        - employment_type: "정규직"
        - salary: "5000000"
        - deadline_at: "2025-05-10"
        - work_days: "주 5일"
        - description: "자세한 설명..."
        - image_file: [파일 업로드]
        ```
    """
    return await service.create_job_posting(
        session=session,
        data=job_posting,
        author_id=current_user.id,
        company_id=current_user.company_id,
        image_file=image_file,
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
) -> dict[str, Any]:
    """채용공고 목록 조회 API
    
    Args:
        skip: 건너뛸 레코드 수 (페이지네이션 offset)
        limit: 가져올 레코드 수 (페이지네이션 limit)
        session: DB 세션
        
    Returns:
        페이지네이션된 채용공고 목록 및 메타데이터
    """
    postings, total_count = await service.list_job_postings(
        session=session, skip=skip, limit=limit
    )
    
    # 부분 필드를 포함하는 결과를 JobPostingResponse로 변환
    posting_responses = []
    for posting_tuple in postings:
        # 튜플 형태의 결과를 딕셔너리로 변환
        posting_dict = {
            "id": posting_tuple[0],
            "title": posting_tuple[1],
            "job_category": posting_tuple[2],
            "work_address": posting_tuple[3],
            "salary": posting_tuple[4],
            "recruit_period_start": posting_tuple[5],
            "recruit_period_end": posting_tuple[6],
            "deadline_at": posting_tuple[7],
            "is_always_recruiting": posting_tuple[8],
            "created_at": posting_tuple[9],
            "updated_at": posting_tuple[10],
            "author_id": posting_tuple[11],
            "company_id": posting_tuple[12],
        }
        # 딕셔너리를 Pydantic 모델로 변환
        posting_responses.append(JobPostingResponse.model_validate(posting_dict))
    
    return {
        "items": posting_responses,
        "total": total_count,
        "skip": skip,
        "limit": limit,
    }


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
) -> dict[str, Any]:
    """채용공고 검색 API
    
    Args:
        keyword: 검색 키워드 (제목, 내용에서 검색)
        location: 근무지 위치
        job_category: 직무 카테고리
        employment_type: 고용 형태
        is_always_recruiting: 상시 채용 여부
        page: 페이지 번호
        limit: 페이지당 결과 수
        sort: 정렬 기준 (latest: 최신순, deadline: 마감일순, salary_high: 연봉 높은순, salary_low: 연봉 낮은순)
        session: DB 세션
        
    Returns:
        페이지네이션된 채용공고 검색 결과 및 메타데이터
    """
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
    
    # 부분 필드를 포함하는 결과를 JobPostingResponse로 변환
    posting_responses = []
    for posting_tuple in postings:
        # 튜플 형태의 결과를 딕셔너리로 변환
        posting_dict = {
            "id": posting_tuple[0],
            "title": posting_tuple[1],
            "job_category": posting_tuple[2],
            "work_address": posting_tuple[3],
            "salary": posting_tuple[4],
            "recruit_period_start": posting_tuple[5],
            "recruit_period_end": posting_tuple[6],
            "deadline_at": posting_tuple[7],
            "is_always_recruiting": posting_tuple[8],
            "created_at": posting_tuple[9],
            "updated_at": posting_tuple[10],
            "author_id": posting_tuple[11],
            "company_id": posting_tuple[12],
        }
        # 딕셔너리를 Pydantic 모델로 변환
        posting_responses.append(JobPostingResponse.model_validate(posting_dict))
    
    return {
        "items": posting_responses,
        "total": total_count,
        "skip": (page - 1) * limit,
        "limit": limit,
    }


@router.get(
    "/popular",
    response_model=PaginatedJobPostingResponse,
    summary="인기 채용공고 목록 조회",
    description="지원자 수가 많은 인기 채용공고를 조회합니다.",
)
async def list_popular_postings(
    limit: int = Query(10, ge=1, le=100, description="가져올 레코드 수"),
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """인기 채용공고 목록 조회 API
    
    Args:
        limit: 가져올 레코드 수
        session: DB 세션
        
    Returns:
        인기 채용공고 목록 및 메타데이터
    """
    postings, total_count = await service.get_popular_job_postings(
        session=session, limit=limit
    )
    
    # JobPosting 객체를 그대로 반환 (Pydantic 모델에서 자동으로 변환)
    return {
        "items": postings,
        "total": total_count,
        "skip": 0,
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
) -> JobPosting:
    """채용공고 상세 조회 API
    
    Args:
        job_posting_id: 채용공고 ID
        session: DB 세션
        
    Returns:
        채용공고 상세 정보
        
    Raises:
        HTTPException: 채용공고가 없을 경우
    """
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
) -> JobPosting:
    """채용공고 수정 API
    
    Args:
        job_posting_id: 채용공고 ID
        data: 수정할 채용공고 데이터
        session: DB 세션
        current_user: 현재 로그인한 기업 사용자
        
    Returns:
        수정된 채용공고 정보
    """
    # 공통 함수를 사용하여 채용공고 조회 및 권한 확인
    await get_posting_with_permission_check(
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
) -> None:
    """채용공고 삭제 API
    
    Args:
        job_posting_id: 채용공고 ID
        session: DB 세션
        current_user: 현재 로그인한 기업 사용자
        
    Returns:
        None
    """
    # 공통 함수를 사용하여 채용공고 조회 및 권한 확인
    await get_posting_with_permission_check(
        job_posting_id=job_posting_id,
        session=session,
        current_user=current_user,
        action_type="삭제"
    )
    
    await service.delete_job_posting(session, job_posting_id)
    return None