from typing import Optional, Union, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc
from fastapi import Depends, HTTPException, status
from datetime import datetime
import logging

from app.domains.job_postings.schemas import JobPostingUpdate, JobPostingCreate, JobCategoryEnum, SortOptions
from app.models.job_postings import JobPosting
from app.models.users import User
from app.domains.job_postings.repository import JobPostingRepository
from app.core.db import get_db_session


# 로거 설정
logger = logging.getLogger(__name__)


# --- 레포지토리 의존성 주입 프로바이더 ---

def get_job_posting_repository(session: AsyncSession = Depends(get_db_session)) -> JobPostingRepository:
    """JobPostingRepository 인스턴스를 생성하여 의존성 주입"""
    return JobPostingRepository(session)


# --- 내부 헬퍼 함수 ---

async def _attach_favorite_status(
    postings: Union[JobPosting, List[JobPosting]],
    user_id: Optional[int],
    repository: JobPostingRepository,
) -> None:
    """주어진 채용 공고(들)에 현재 사용자의 즐겨찾기 상태(`is_favorited`)를 설정합니다."""
    # 1. 입력 데이터 확인 및 전처리
    if not postings:
        return # 공고가 없으면 종료

    # 단일 객체도 리스트로 처리하기 위함
    is_single = False
    if isinstance(postings, JobPosting):
        is_single = True
        posting_list = [postings]
    else:
        posting_list = postings

    # 2. 사용자 로그인 여부 확인 및 기본값 설정
    if user_id is None or not posting_list:
        # 비로그인 상태이거나 공고 목록이 비어있으면 모든 공고의 is_favorited를 None으로 설정
        for p in posting_list:
            setattr(p, 'is_favorited', None)
        return

    # 3. 즐겨찾기 정보 조회
    posting_ids = [p.id for p in posting_list] # 조회할 공고 ID 목록 추출
    favorited_posting_ids = await repository.get_favorited_posting_ids(user_id, posting_ids) # 레포지토리 통해 즐겨찾기된 ID 조회

    # 4. 각 공고에 즐겨찾기 상태 설정
    for p in posting_list:
        setattr(p, 'is_favorited', p.id in favorited_posting_ids) # 해당 공고 ID가 즐겨찾기 목록에 있는지 여부 설정


# --- 서비스 함수 --- (비즈니스 로직 담당)

async def create_job_posting(
    job_posting_data: JobPostingCreate,
    author_id: int,
    company_id: int,
    repository: JobPostingRepository = Depends(get_job_posting_repository),
) -> JobPosting:
    """채용 공고 생성 서비스"""
    # 1. ORM 모델에 맞게 데이터 준비
    orm_data = job_posting_data.model_dump(exclude_unset=True) # 입력 스키마에서 ORM 데이터 추출
    orm_data["author_id"] = author_id # 작성자 ID 추가
    orm_data["company_id"] = company_id # 회사 ID 추가

    try:
        # 2. 레포지토리를 통해 공고 생성
        job_posting = await repository.create(orm_data)
        # 3. 생성된 공고에 기본 즐겨찾기 상태 설정 (생성 직후이므로 None)
        job_posting.is_favorited = None
        return job_posting
    except Exception as e:
        # 4. 오류 처리
        logger.exception("Error creating job posting") # 예외 정보와 함께 에러 로그 기록
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채용 공고 생성 중 오류가 발생했습니다."
        )


async def list_job_postings(
    repository: JobPostingRepository = Depends(get_job_posting_repository),
    skip: int = 0,
    limit: int = 10,
    user_id: Optional[int] = None
) -> tuple[List[JobPosting], int]:
    """채용 공고 목록 조회 (페이지네이션, 로그인 시 즐겨찾기 여부 포함)"""
    # 1. 전체 공고 수 조회
    total_count = await repository.count_all()

    # 2. 공고가 없으면 빈 목록 반환
    if total_count == 0:
        return [], 0

    # 3. 페이지네이션 적용하여 공고 목록 조회
    postings = await repository.list_all(skip=skip, limit=limit)

    # 4. 로그인 사용자라면 즐겨찾기 상태 첨부
    await _attach_favorite_status(postings, user_id, repository)

    # 5. 결과 반환
    return postings, total_count


async def get_job_posting(
    job_posting_id: int,
    repository: JobPostingRepository = Depends(get_job_posting_repository),
    user_id: Optional[int] = None
) -> JobPosting | None:
    """ID로 특정 채용 공고 조회 (로그인 시 즐겨찾기 여부 포함)"""
    # 1. ID로 공고 조회
    job_posting = await repository.get_by_id(job_posting_id)

    # 2. 공고가 없으면 None 반환 (라우터에서 404 처리)
    if not job_posting:
        return None

    # 3. 로그인 사용자라면 즐겨찾기 상태 첨부
    await _attach_favorite_status(job_posting, user_id, repository)

    # 4. 결과 반환
    return job_posting


async def update_job_posting(
    job_posting_id: int,
    data: JobPostingUpdate,
    repository: JobPostingRepository = Depends(get_job_posting_repository),
) -> JobPosting | None:
    """채용 공고 업데이트 서비스"""
    # 1. 업데이트할 데이터 추출 (변경되지 않은 필드는 제외)
    update_data = data.model_dump(exclude_unset=True)

    # 2. 업데이트할 데이터가 없으면 기존 공고 정보 반환
    if not update_data:
        job_posting = await repository.get_by_id(job_posting_id)
        if job_posting:
            # 업데이트가 없어도 즐겨찾기 상태는 None으로 초기화 (업데이트 응답이므로)
            job_posting.is_favorited = None
        return job_posting # 원본 공고 반환 (없으면 None)

    try:
        # 3. 레포지토리를 통해 공고 업데이트
        updated_posting = await repository.update(job_posting_id, update_data)

        # 4. 업데이트 대상이 없으면 None 반환 (라우터에서 404 처리 가능)
        if updated_posting is None:
            return None

        # 5. 업데이트된 공고에 기본 즐겨찾기 상태 설정 (None)
        updated_posting.is_favorited = None
        return updated_posting
    except Exception as e:
        # 6. 오류 처리
        logger.exception(f"Error updating job posting {job_posting_id}") # 예외 정보와 함께 에러 로그 기록
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채용 공고 업데이트 중 오류가 발생했습니다."
        )


async def delete_job_posting(
    job_posting_id: int,
    repository: JobPostingRepository = Depends(get_job_posting_repository),
) -> bool:
    """채용 공고 삭제 서비스. 성공 시 True, 실패(대상 없음 포함) 시 False 반환."""
    try:
        # 1. 레포지토리를 통해 공고 삭제 시도
        success = await repository.delete(job_posting_id)
        # 2. 삭제 성공 여부 반환 (repository.delete 결과)
        return success
    except Exception as e:
        # 3. 오류 처리
        logger.exception(f"Error deleting job posting {job_posting_id}") # 예외 정보와 함께 에러 로그 기록
        # 삭제 실패 시 False 반환 (라우터에서 500 처리)
        return False


async def search_job_postings(
    repository: JobPostingRepository = Depends(get_job_posting_repository),
    keyword: str | None = None,
    location: str | None = None,
    job_category: JobCategoryEnum | None = None,
    employment_type: str | None = None,
    is_always_recruiting: bool | None = None,
    page: int = 1,
    limit: int = 10,
    sort: SortOptions = SortOptions.LATEST,
    user_id: Optional[int] = None
) -> tuple[List[JobPosting], int]:
    """채용 공고 검색 (필터링, 정렬, 페이지네이션, 로그인 시 즐겨찾기 여부 포함)"""
    # 1. 검색 필터 조건 생성
    filters = []
    if keyword:
        # 키워드는 제목, 설명, 요약에서 검색 (ILIKE는 대소문자 구분 없음)
        filters.append(
            JobPosting.title.ilike(f"%{keyword}%") |
            JobPosting.description.ilike(f"%{keyword}%") |
            JobPosting.summary.ilike(f"%{keyword}%")
        )
    if location:
        filters.append(JobPosting.work_address.ilike(f"%{location}%"))
    if job_category:
        filters.append(JobPosting.job_category == job_category.value)
    if employment_type:
        filters.append(JobPosting.employment_type == employment_type)
    if is_always_recruiting is not None:
        filters.append(JobPosting.is_always_recruiting == is_always_recruiting)

    # 2. 정렬 조건 생성
    if sort == SortOptions.LATEST:
        order_by_clause = desc(JobPosting.created_at)
    elif sort == SortOptions.SALARY_HIGH:
        order_by_clause = desc(JobPosting.salary)
    elif sort == SortOptions.SALARY_LOW:
        order_by_clause = JobPosting.salary
    else: # 기본값: 최신순
        order_by_clause = desc(JobPosting.created_at)

    # 3. 필터링된 전체 공고 수 조회
    total_count = await repository.count_search(filters=filters)

    # 4. 검색 결과가 없으면 빈 목록 반환
    if total_count == 0:
        return [], 0

    # 5. 페이지네이션 적용하여 공고 검색
    skip = (page - 1) * limit
    postings = await repository.search(
        filters=filters,
        order_by_clause=order_by_clause,
        skip=skip,
        limit=limit
    )

    # 6. 로그인 사용자라면 즐겨찾기 상태 첨부
    await _attach_favorite_status(postings, user_id, repository)

    # 7. 결과 반환
    return postings, total_count


async def get_popular_job_postings(
    repository: JobPostingRepository = Depends(get_job_posting_repository),
    limit: int = 10,
    user_id: Optional[int] = None
) -> tuple[List[JobPosting], int]:
    """인기 채용 공고 목록 조회 (지원자 수 기준, 로그인 시 즐겨찾기 여부 포함)"""
    # 1. 레포지토리 통해 인기 공고 목록 조회 (지원자 수 기준 정렬됨)
    postings = await repository.list_popular(limit=limit)

    # 2. 로그인 사용자라면 즐겨찾기 상태 첨부
    await _attach_favorite_status(postings, user_id, repository)

    # 3. 조회된 공고 수 계산 및 결과 반환
    total_count = len(postings) # 인기 공고는 별도 count 없이 조회된 개수가 전체
    return postings, total_count


async def get_popular_job_postings_for_user_age_group(
    user: User,
    repository: JobPostingRepository = Depends(get_job_posting_repository),
    limit: int = 10
) -> tuple[List[JobPosting], int]:
    """
    로그인한 사용자의 나이대에 맞는 인기 채용 공고 목록 조회.
    사용자 생년월일 정보 필요.
    """
    # 1. 사용자 정보 및 생년월일 유효성 검사
    if not user or not user.birthday:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="생년월일 정보가 없습니다. 마이페이지에서 생년월일을 등록해주세요.")
    try:
        # 생년월일 파싱 (앞 10자리 YYYY-MM-DD 형식 가정)
        birth = user.birthday[:10]
        birth_date = datetime.strptime(birth, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="생년월일 형식이 올바르지 않습니다. (예: 1965-05-10)")

    # 2. 사용자 나이 및 연령대 계산
    today = datetime.today().date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    age_start = (age // 10) * 10 # 10대, 20대, 30대... 시작 나이
    age_end = age_start + 10 # 10대 (10~19), 20대 (20~29)... 끝 나이

    # 3. 레포지토리 통해 해당 연령대 인기 공고 목록 조회
    postings = await repository.list_popular_by_age_group(
        age_start=age_start,
        age_end=age_end,
        limit=limit
    )

    # 4. 로그인 사용자 즐겨찾기 상태 첨부 (user.id 사용)
    await _attach_favorite_status(postings, user.id, repository)

    # 5. 조회된 공고 수 계산 및 결과 반환
    total_count = len(postings) # 인기 공고는 별도 count 없이 조회된 개수가 전체
    return postings, total_count