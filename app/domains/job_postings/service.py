from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, exists, select, and_
from fastapi import UploadFile, HTTPException, status

from app.domains.job_postings.schemas import JobPostingUpdate, JobPostingCreate
from app.models.job_postings import JobPosting
from app.models.job_applications import JobApplication
from app.models.favorites import Favorite
from app.core.utils import upload_image_to_ncp


async def create_job_posting(
    session: AsyncSession,
    job_posting_data: JobPostingCreate,
    author_id: int,
    company_id: int,
    image_file: UploadFile | None = None
) -> JobPosting:
    """채용 공고 생성 (이미지 포함 가능)"""
    image_url = None
    if image_file:
        try:
            image_url = await upload_image_to_ncp(image_file, folder="job_postings")
        except Exception as e:
            print(f"Warning: 이미지 업로드 실패 - {e}. 이미지 없이 공고를 생성합니다.")
            # 필요에 따라 HTTPException을 발생시킬 수 있습니다.
            # raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="이미지 업로드 중 오류 발생")
            # 여기서는 일단 이미지 없이 진행하도록 None 유지

    # JobPostingCreate 모델에서 ORM 모델에 필요한 데이터 추출
    orm_data = job_posting_data.model_dump(exclude={"postings_image"})

    # JobPosting ORM 객체 생성
    job_posting = JobPosting(
        **orm_data,
        author_id=author_id,
        company_id=company_id,
        postings_image=image_url # 업로드된 이미지 URL 또는 None
    )

    try:
        session.add(job_posting)
        await session.commit()
        await session.refresh(job_posting)
        # 생성된 공고 객체에 is_favorited 속성 추가 (기본값 None)
        job_posting.is_favorited = None
        return job_posting
    except Exception as e:
        await session.rollback()
        print(f"Error: 채용 공고 생성 중 데이터베이스 오류 발생 - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채용 공고 생성 중 오류가 발생했습니다."
        )


async def list_job_postings(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    user_id: Optional[int] = None
) -> tuple[list[JobPosting], int]:
    """채용 공고 목록 조회 (페이지네이션, 즐겨찾기 여부 포함)"""
    # 전체 개수 조회 쿼리
    count_query = select(func.count(JobPosting.id))
    total_count = await session.scalar(count_query)

    if total_count == 0:
        return [], 0

    # 목록 조회 쿼리 (최신순 정렬)
    list_query = (
        select(JobPosting)
        .order_by(desc(JobPosting.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(list_query)
    postings = list(result.scalars().all()) # 결과를 리스트로 변환

    # 로그인 사용자이고 공고 목록이 있으면 즐겨찾기 정보 조회
    if user_id and postings:
        posting_ids = [p.id for p in postings]
        # 현재 페이지 공고 ID들에 대해 사용자가 즐겨찾기한 ID 목록 조회
        favorite_query = select(Favorite.job_posting_id).where(
            and_( # 명시적으로 AND 조건 사용
                Favorite.user_id == user_id,
                Favorite.job_posting_id.in_(posting_ids)
            )
        )
        favorite_result = await session.execute(favorite_query)
        favorited_posting_ids = {row[0] for row in favorite_result} # Set으로 변환하여 빠르게 확인

        # 각 공고 객체에 is_favorited 속성 설정
        for posting in postings:
            posting.is_favorited = posting.id in favorited_posting_ids
    else:
        # 비로그인 사용자이거나 공고가 없으면 모든 공고의 is_favorited를 None으로 설정
        for posting in postings:
            posting.is_favorited = None

    return postings, total_count # 수정된 공고 리스트 반환


async def get_job_posting(
    session: AsyncSession,
    job_posting_id: int,
    user_id: Optional[int] = None
) -> JobPosting | None:
    """ID로 특정 채용 공고 조회 (즐겨찾기 여부 포함)"""
    # session.get으로 PK 조회
    job_posting = await session.get(JobPosting, job_posting_id)
    if not job_posting:
        return None # 공고 없으면 None 반환

    # 즐겨찾기 여부 확인 및 설정
    if user_id:
        # 로그인한 경우, 즐겨찾기 여부 확인 쿼리
        favorite_exists_query = select(
            exists().where(
                and_( # 명시적으로 AND 조건 사용
                    Favorite.user_id == user_id,
                    Favorite.job_posting_id == job_posting_id
                )
            )
        )
        is_favorited = await session.scalar(favorite_exists_query)
        # scalar 결과가 True/False/None 일 수 있으므로 명확히 처리
        job_posting.is_favorited = bool(is_favorited) # bool()은 None을 False로 변환
    else:
        # 비로그인 시 또는 user_id 없을 시 None으로 설정
        job_posting.is_favorited = None

    return job_posting


async def update_job_posting(
    session: AsyncSession,
    job_posting_id: int,
    data: JobPostingUpdate
) -> JobPosting | None:
    """채용 공고 업데이트"""
    # 수정할 공고 조회 (여기서는 user_id 필요 없음)
    job_posting = await session.get(JobPosting, job_posting_id)
    if not job_posting:
        return None

    # 변경된 데이터만 추출
    update_data = data.model_dump(exclude_unset=True)

    # 업데이트 할 내용이 없으면 그대로 반환 (is_favorited는 None으로 설정)
    if not update_data:
        job_posting.is_favorited = None # 응답 스키마 일관성
        return job_posting

    # 객체 속성 업데이트
    for key, value in update_data.items():
        setattr(job_posting, key, value)

    try:
        await session.commit()
        await session.refresh(job_posting)
        # 업데이트 후 is_favorited 정보는 없음 (None으로 설정)
        job_posting.is_favorited = None # 응답 스키마 일관성
        return job_posting
    except Exception as e:
        await session.rollback()
        print(f"Error: 채용 공고 업데이트 중 데이터베이스 오류 발생 - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채용 공고 업데이트 중 오류가 발생했습니다."
        )


async def delete_job_posting(
    session: AsyncSession,
    job_posting_id: int
) -> bool: # 반환 타입을 bool로 변경하여 성공/실패 명시
    """채용 공고 삭제"""
    job_posting = await session.get(JobPosting, job_posting_id)
    if not job_posting:
        return False # 삭제 대상 없음

    try:
        await session.delete(job_posting)
        await session.commit()
        return True # 삭제 성공
    except Exception as e:
        await session.rollback()
        print(f"Error: 채용 공고 삭제 중 데이터베이스 오류 발생 - {e}")
        # 필요하다면 여기서 HTTPException 발생 또는 False 반환
        # raise HTTPException(...)
        return False # 삭제 실패


async def search_job_postings(
    session: AsyncSession,
    keyword: str | None = None,
    location: str | None = None,
    job_category: str | None = None, # Enum 값(value)으로 검색 가정
    employment_type: str | None = None,
    is_always_recruiting: bool | None = None,
    page: int = 1,
    limit: int = 10,
    sort: str = "latest", # 정렬 기준
    user_id: Optional[int] = None # user_id 파라미터 추가
) -> tuple[list[JobPosting], int]:
    """채용 공고 검색 (필터링, 정렬, 페이지네이션, 즐겨찾기 여부 포함)"""
    # 기본 쿼리 생성
    base_query = select(JobPosting)
    filters = []

    # 검색 조건(필터) 동적 추가
    if keyword:
        filters.append(
            JobPosting.title.ilike(f"%{keyword}%") | # 제목 또는 내용 검색 (OR)
            JobPosting.description.ilike(f"%{keyword}%")
        )
    if location:
        filters.append(JobPosting.work_address.ilike(f"%{location}%"))
    if job_category:
        filters.append(JobPosting.job_category == job_category) # Enum 값으로 정확히 일치 가정
    if employment_type:
        filters.append(JobPosting.employment_type == employment_type)
    if is_always_recruiting is not None:
        filters.append(JobPosting.is_always_recruiting == is_always_recruiting)

    # 필터 적용 (모든 조건 AND)
    if filters:
        base_query = base_query.where(*filters) # and_() 불필요, where은 기본 AND

    # 필터링된 전체 개수 계산 (서브쿼리 사용)
    count_query = select(func.count()).select_from(base_query.subquery())
    total_count = await session.scalar(count_query)

    # 결과가 없으면 빈 리스트 반환
    if total_count == 0:
        return [], 0

    # 정렬 기준(Clause) 결정
    if sort == "latest":
        order_by_clause = desc(JobPosting.created_at)
    elif sort == "salary_high":
        order_by_clause = desc(JobPosting.salary)
    elif sort == "salary_low":
        order_by_clause = JobPosting.salary # 기본 오름차순
    else:
        # 기본 정렬 기준 (예: 최신순) 또는 에러 처리
        order_by_clause = desc(JobPosting.created_at)

    # 페이지네이션 및 정렬 적용
    search_query = (
        base_query
        .order_by(order_by_clause)
        .offset((page - 1) * limit)
        .limit(limit)
    )

    result = await session.execute(search_query)
    postings = list(result.scalars().all()) # 결과를 리스트로 변환

    # 로그인 사용자이고 공고 목록이 있으면 즐겨찾기 정보 조회
    if user_id and postings:
        posting_ids = [p.id for p in postings]
        favorite_query = select(Favorite.job_posting_id).where(
            and_(
                Favorite.user_id == user_id,
                Favorite.job_posting_id.in_(posting_ids)
            )
        )
        favorite_result = await session.execute(favorite_query)
        favorited_posting_ids = {row[0] for row in favorite_result}

        # 각 공고 객체에 is_favorited 속성 설정
        for posting in postings:
            posting.is_favorited = posting.id in favorited_posting_ids
    else:
        # 비로그인 사용자이거나 공고가 없으면 모든 공고의 is_favorited를 None으로 설정
        for posting in postings:
            posting.is_favorited = None

    return postings, total_count


async def get_popular_job_postings(
    session: AsyncSession,
    limit: int = 10,
    user_id: Optional[int] = None
) -> tuple[list[JobPosting], int]: # total_count는 조회된 인기 공고 수
    """인기 채용 공고 조회 (지원자 수 기준, 즐겨찾기 여부 포함)"""

    # 지원자 수를 계산하는 서브쿼리 생성
    applications_count_sq = (
        select(
            JobApplication.job_posting_id,
            func.count().label('app_count') # 지원자 수 계산
        )
        .group_by(JobApplication.job_posting_id) # 공고 ID 별로 그룹화
        .subquery('app_counts') # 서브쿼리로 사용
    )

    # 채용공고와 지원자 수 서브쿼리 조인 (Outer Join: 지원자 없는 공고도 포함)
    list_query = (
        select(JobPosting)
        .outerjoin(applications_count_sq, JobPosting.id == applications_count_sq.c.job_posting_id)
        # 인기순 정렬: 지원자 수(app_count) 내림차순, 같으면 최신 공고 순
        # coalesce: 지원자 없는 경우(NULL) 0으로 처리하여 정렬
        .order_by(desc(func.coalesce(applications_count_sq.c.app_count, 0)), desc(JobPosting.created_at))
        .limit(limit) # 상위 N개 제한
    )

    # 쿼리 실행 및 결과 가져오기
    result = await session.execute(list_query)
    postings = list(result.scalars().all()) # 결과를 리스트로 변환

    # 로그인 사용자이고 공고 목록이 있으면 즐겨찾기 정보 조회 (list_job_postings와 동일 로직)
    if user_id and postings:
        posting_ids = [p.id for p in postings]
        favorite_query = select(Favorite.job_posting_id).where(
            and_(
                Favorite.user_id == user_id,
                Favorite.job_posting_id.in_(posting_ids)
            )
        )
        favorite_result = await session.execute(favorite_query)
        favorited_posting_ids = {row[0] for row in favorite_result}

        for posting in postings:
            posting.is_favorited = posting.id in favorited_posting_ids
    else:
        for posting in postings:
            posting.is_favorited = None

    # total_count는 조회된 인기 공고 수 반환
    total_count = len(postings)
    return postings, total_count