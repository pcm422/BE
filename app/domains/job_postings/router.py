from typing import Optional
from enum import Enum

from fastapi import APIRouter, Depends, Query, status, UploadFile, File
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.utils import get_current_company_user, get_current_user_optional
from app.domains.job_postings import service
from app.domains.job_postings.schemas import (
                                                JobPostingResponse,
                                                JobPostingUpdate,
                                                PaginatedJobPostingResponse,
                                                JobPostingCreateFormData) # 스키마 임포트
from app.models.company_users import CompanyUser
from app.models.job_postings import JobPosting, JobCategoryEnum # 모델 임포트
from app.models.users import User # User 모델 import 추가

# 정렬 옵션 정의 Enum
class SortOptions(str, Enum):
    LATEST = "latest"
    SALARY_HIGH = "salary_high"
    SALARY_LOW = "salary_low"

# API 라우터 설정 (prefix, tags 지정)
router = APIRouter(prefix="/posting", tags=["채용공고"])


# --- Helper Functions (라우터 내부용) ---

async def get_posting_or_404(
    session: AsyncSession, job_posting_id: int, user_id: int | None = None
) -> JobPosting:
    """ID로 채용공고를 조회하고 없으면 404 에러 발생시키는 헬퍼 함수 (user_id 전달)"""
    # 서비스 계층 함수 호출 시 user_id 전달
    posting = await service.get_job_posting(session, job_posting_id, user_id=user_id)
    if not posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채용공고를 찾을 수 없습니다.")
    return posting


async def check_posting_permission(
    posting: JobPosting, current_user: CompanyUser, action_type: str = "접근"
):
    """채용공고에 대한 현재 사용자의 권한(소유권) 확인 헬퍼 함수"""
    # 작성자와 현재 사용자가 다르면 403 예외 발생
    if posting.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"본인 공고만 {action_type}할 수 있습니다.")


# --- API Endpoints ---

@router.post(
    "/",
    response_model=JobPostingResponse, # 응답 형식 지정
    status_code=status.HTTP_201_CREATED, # 성공 상태 코드
    summary="채용공고 생성",
    description="로그인된 기업 담당자가 새로운 채용공고를 등록합니다. 이미지 파일을 함께 업로드할 수 있습니다.",
)
async def create_job_posting(
    # 의존성 주입: Form 데이터, 이미지 파일, DB 세션, 현재 사용자 정보
    form_data: JobPostingCreateFormData = Depends(), # Form 데이터 처리 클래스
    image_file: UploadFile = File(None, description="채용공고 이미지 파일 (선택사항)"),
    session: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
) -> JobPosting: # 성공 시 JobPosting ORM 객체 반환 (response_model에 의해 변환됨)
    """채용공고 생성 API 엔드포인트"""
    try:
        # 1. Form 데이터를 JobPostingCreate Pydantic 모델로 변환/검증 (스키마 클래스 내 메서드 사용)
        job_posting_create_data = form_data.parse_to_job_posting_create(postings_image_url=None)

        # 2. 서비스 계층 함수 호출하여 공고 생성 로직 수행
        created_posting = await service.create_job_posting(
            session=session,
            job_posting_data=job_posting_create_data, # 검증된 데이터 전달
            author_id=current_user.id,
            company_id=current_user.company_id,
            image_file=image_file, # 이미지 파일 전달
        )
        # 3. 생성된 공고 객체 반환
        return created_posting
    except HTTPException as http_exc:
        # 스키마 변환/검증 또는 서비스 로직에서 발생한 HTTP 예외는 그대로 전달
        raise http_exc
    except Exception as e:
        # 그 외 예상치 못한 서버 오류 처리 (로그 출력 + 500 에러 반환)
        print(f"Error: 채용 공고 생성 라우터 오류 - {e}") # 실제 운영에서는 logger 사용 권장
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"채용 공고 생성 중 서버 오류 발생: {e}"
        )


@router.get(
    "/",
    response_model=PaginatedJobPostingResponse,
    summary="채용공고 목록 조회",
    description="채용공고 목록을 페이지네이션하여 조회합니다. 로그인 시 즐겨찾기 여부가 포함됩니다.",
)
async def list_postings(
    skip: int = Query(0, ge=0, description="건너뛸 레코드 수"),
    limit: int = Query(10, ge=1, le=100, description="가져올 레코드 수"),
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> PaginatedJobPostingResponse:
    """채용공고 목록 조회 API 엔드포인트 (즐겨찾기 포함)"""
    user_id = current_user.id if current_user else None

    postings, total_count = await service.list_job_postings(
        session=session, skip=skip, limit=limit, user_id=user_id
    )

    # 페이지네이션 응답 객체 생성 및 반환 (items의 각 요소가 is_favorited를 가짐)
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
    description="키워드 및 필터 기반으로 채용공고를 검색합니다. 로그인 시 즐겨찾기 여부가 포함됩니다.",
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
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> PaginatedJobPostingResponse:
    """채용공고 검색 API 엔드포인트 (즐겨찾기 포함)"""
    user_id = current_user.id if current_user else None

    postings, total_count = await service.search_job_postings(
        session=session,
        keyword=keyword,
        location=location,
        job_category=job_category.value if job_category else None,
        employment_type=employment_type,
        is_always_recruiting=is_always_recruiting,
        page=page,
        limit=limit,
        sort=sort.value,
        user_id=user_id
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
    description="지원자 수가 많은 인기 채용공고를 조회합니다. 로그인 시 즐겨찾기 여부가 포함됩니다.",
)
async def list_popular_postings(
    limit: int = Query(10, ge=1, le=100, description="가져올 레코드 수"),
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> PaginatedJobPostingResponse:
    """인기 채용공고 목록 조회 API 엔드포인트 (즐겨찾기 포함)"""
    user_id = current_user.id if current_user else None

    postings, total_count = await service.get_popular_job_postings(
        session=session, limit=limit, user_id=user_id
    )

    # total_count의 의미에 맞게 응답 구성 필요
    return PaginatedJobPostingResponse(
        items=postings,
        total=total_count,
        skip=0,
        limit=limit,
    )


@router.get(
    "/popular-by-my-age",
    response_model=PaginatedJobPostingResponse,
    summary="내 연령대 인기 채용공고 목록 조회",
    description="로그인한 사용자의 나이대(40~50, 50~60, 60~70)에서 인기 있는 공고를 조회합니다.",
)
async def list_popular_postings_by_my_age(
    limit: int = Query(10, ge=1, le=100, description="가져올 레코드 수"),
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> PaginatedJobPostingResponse:
    """
    내 연령대 인기 채용공고 목록 조회 API 엔드포인트
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    postings, total_count = await service.get_popular_job_postings_for_user_age_group(
        session=session,
        user=current_user,
        limit=limit
    )

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
    description="특정 채용공고의 상세정보를 조회합니다. 로그인 시 즐겨찾기 여부가 포함됩니다.",
)
async def get_posting(
    job_posting_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> JobPosting:
    user_id = current_user.id if current_user else None
    posting = await get_posting_or_404(session, job_posting_id, user_id=user_id)
    return posting


@router.patch(
    "/{job_posting_id}", # 경로 파라미터로 공고 ID 받음
    response_model=JobPostingResponse, # 성공 시 업데이트된 공고 정보 반환
    summary="채용공고 수정",
    description="로그인된 기업 담당자가 자신이 올린 채용공고를 수정합니다.",
)
async def update_posting(
    # 의존성 주입: 경로 파라미터, 요청 본문(수정 데이터), DB 세션, 현재 사용자
    job_posting_id: int,
    data: JobPostingUpdate, # 요청 본문은 JobPostingUpdate 스키마로 검증
    session: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
) -> JobPosting: # 성공 시 ORM 객체 반환
    """채용공고 수정 API 엔드포인트"""
    # 1. 공고 조회 (없으면 404)
    posting = await get_posting_or_404(session, job_posting_id)

    # 2. 수정 권한 확인 (본인 공고인지)
    await check_posting_permission(posting, current_user, action_type="수정")

    # 3. 서비스 계층 호출 (업데이트 로직 수행)
    updated_posting = await service.update_job_posting(
        session=session, job_posting_id=job_posting_id, data=data
    )
    # 4. 서비스 결과 확인 (정상 처리 시 업데이트된 객체, 실패/못찾음 시 None 예상)
    if updated_posting is None:
        # 서비스에서 None 반환 시 (예: DB 오류 외 다른 이유로 실패) 500 에러 발생
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="공고 업데이트 처리 중 오류 발생")

    # 5. 업데이트된 공고 반환
    return updated_posting


@router.delete(
    "/{job_posting_id}", # 경로 파라미터로 공고 ID 받음
    status_code=status.HTTP_204_NO_CONTENT, # 성공 시 응답 본문 없음
    summary="채용공고 삭제",
    description="로그인된 기업 담당자가 자신이 올린 채용공고를 삭제합니다.",
)
async def delete_posting(
    # 의존성 주입: 경로 파라미터, DB 세션, 현재 사용자
    job_posting_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
) -> None: # 성공 시 반환값 없음
    """채용공고 삭제 API 엔드포인트"""
    # 1. 공고 조회 (없으면 404)
    posting = await get_posting_or_404(session, job_posting_id)

    # 2. 삭제 권한 확인 (본인 공고인지)
    await check_posting_permission(posting, current_user, action_type="삭제")

    # 3. 서비스 계층 호출 (삭제 로직 수행)
    # 서비스 함수는 성공 시 True, 실패 시 False 반환
    success = await service.delete_job_posting(session=session, job_posting_id=job_posting_id)

    # 4. 서비스 호출 결과 확인
    if not success:
        # 서비스에서 False 반환 시 (삭제 실패 또는 DB 오류)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채용 공고 삭제 중 오류가 발생했습니다."
        )

    # 5. 성공 시 None 반환하여 204 응답 처리
    return None