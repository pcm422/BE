from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from fastapi import UploadFile, HTTPException, status

from app.domains.job_postings.schemas import JobPostingUpdate, JobPostingCreate
from app.models.job_postings import JobPosting
from app.models.job_applications import JobApplication
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
            # 이미지 파일명을 고유하게 만들거나 그대로 사용 (utils 함수 정책에 따름)
            image_url = await upload_image_to_ncp(image_file, folder="job_postings")
        except Exception as e:
            # 이미지 업로드 실패 시 로깅 또는 에러 처리 (현재는 URL 없이 진행)
            print(f"Warning: 이미지 업로드 실패 - {e}. 이미지 없이 공고를 생성합니다.")
            # 필요시 여기서 HTTPException 발생 가능
            # raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="이미지 업로드 중 오류 발생")

    # JobPostingCreate 모델에서 ORM 모델에 필요한 데이터 추출
    # author_id, company_id 는 파라미터로 받고, postings_image는 위에서 처리
    # job_posting_data는 이미 유효성 검사를 통과한 상태
    orm_data = job_posting_data.model_dump(exclude={"postings_image"}) # 이미지 필드는 별도 처리

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
        return job_posting
    except Exception as e:
        await session.rollback()
        # 데이터베이스 오류는 서버 내부 오류로 처리
        print(f"Error: 채용 공고 생성 중 데이터베이스 오류 발생 - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채용 공고 생성 중 오류가 발생했습니다."
        )


async def list_job_postings(
    session: AsyncSession, skip: int = 0, limit: int = 10
) -> tuple[list[JobPosting], int]:
    """채용 공고 목록 조회 (페이지네이션)"""
    # 전체 개수 조회 쿼리
    count_query = select(func.count(JobPosting.id))
    total_count = await session.scalar(count_query) # scalar_one 사용 가능 (결과가 항상 1개이므로)

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
    postings = result.scalars().all()

    return list(postings), total_count


async def get_job_posting(
    session: AsyncSession, job_posting_id: int
) -> JobPosting | None:
    """ID로 특정 채용 공고 조회"""
    # scalars().first()는 결과가 없으면 None 반환
    # result = await session.execute(
    #     select(JobPosting)
    #     .where(JobPosting.id == job_posting_id)
    #     # .execution_options(populate_existing=True) # get 사용 시 불필요
    # )
    # return result.scalars().first()
    result = await session.get(JobPosting, job_posting_id, options=[]) # get 사용 시 populate_existing 불필요
    return result


async def update_job_posting(
    session: AsyncSession, job_posting_id: int, data: JobPostingUpdate
) -> JobPosting | None:
    """채용 공고 업데이트"""
    job_posting = await get_job_posting(session, job_posting_id)
    if not job_posting:
        return None # 또는 HTTPException(status_code=404) 발생

    # 변경된 데이터만 추출 (값이 None인 경우는 업데이트에서 제외하지 않음, 명시적으로 None으로 설정 가능)
    update_data = data.model_dump(exclude_unset=False) # exclude_unset=False 로 변경하여 None 값도 업데이트 가능하게

    if not update_data: # 업데이트 할 내용이 없으면 그대로 반환
        return job_posting

    for key, value in update_data.items():
        setattr(job_posting, key, value)

    try:
        await session.commit()
        await session.refresh(job_posting)
        return job_posting
    except Exception as e:
        await session.rollback()
        print(f"Error: 채용 공고 업데이트 중 데이터베이스 오류 발생 - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채용 공고 업데이트 중 오류가 발생했습니다."
        )


async def delete_job_posting(
    session: AsyncSession, job_posting_id: int
) -> JobPosting | None:
    """채용 공고 삭제"""
    job_posting = await get_job_posting(session, job_posting_id)
    if not job_posting:
        return None # 또는 HTTPException(status_code=404) 발생

    try:
        await session.delete(job_posting)
        await session.commit()
        # 삭제된 객체는 더 이상 접근 불가하므로 None 또는 다른 값 반환 고려
        # return job_posting # 이 상태는 만료된(expired) 상태일 수 있음
        return job_posting # 삭제 성공 시 객체 반환 (호출부에서 상태 확인 필요 시)
    except Exception as e:
        await session.rollback()
        print(f"Error: 채용 공고 삭제 중 데이터베이스 오류 발생 - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채용 공고 삭제 중 오류가 발생했습니다."
        )


async def search_job_postings(
    session: AsyncSession,
    keyword: str | None = None,
    location: str | None = None,
    job_category: str | None = None, # Enum 값(value)으로 검색
    employment_type: str | None = None,
    is_always_recruiting: bool | None = None,
    page: int = 1,
    limit: int = 10,
    sort: str = "latest" # 정렬 기준
) -> tuple[list[JobPosting], int]:
    """채용 공고 검색 (필터링, 정렬, 페이지네이션)"""
    base_query = select(JobPosting)
    filters = []

    # 검색 조건 추가
    if keyword:
        filters.append(
             JobPosting.title.ilike(f"%{keyword}%") |
             JobPosting.description.ilike(f"%{keyword}%")
        )
    if location:
        filters.append(JobPosting.work_address.ilike(f"%{location}%"))
    if job_category:
        # Enum.value 로 검색
        filters.append(JobPosting.job_category == job_category)
    if employment_type:
        filters.append(JobPosting.employment_type == employment_type)
    if is_always_recruiting is not None:
        filters.append(JobPosting.is_always_recruiting == is_always_recruiting)

    if filters:
        base_query = base_query.where(*filters)

    # 전체 개수 조회 (필터 적용 후)
    # count_query = select(func.count(1)).select_from(
    #     base_query.alias("filtered_postings")
    # )
    count_query = select(func.count(JobPosting.id)).select_from(base_query.subquery()) # subquery 사용
    total_count = await session.scalar(count_query)

    if total_count == 0:
        return [], 0

    # 정렬 적용
    if sort == "latest":
        order_by_clause = desc(JobPosting.created_at)
    elif sort == "deadline":
        # base_query = base_query.order_by(JobPosting.deadline_at)
        order_by_clause = JobPosting.deadline_at # 마감일 오름차순 (가까운 순)
    elif sort == "salary_high":
        # base_query = base_query.order_by(desc(JobPosting.salary))
        order_by_clause = desc(JobPosting.salary)
    elif sort == "salary_low":
        # base_query = base_query.order_by(JobPosting.salary)
        order_by_clause = JobPosting.salary # 급여 오름차순
    else: # 기본 정렬 (최신순)
        order_by_clause = desc(JobPosting.created_at)

    # 페이지네이션 적용
    skip = (page - 1) * limit
    # base_query = base_query.offset(skip).limit(limit)
    list_query = base_query.order_by(order_by_clause).offset(skip).limit(limit)

    # 쿼리 실행 - scalars()를 사용하여 ORM 객체 반환
    result = await session.execute(list_query)
    # total_count = await session.scalar(count_query)

    postings = result.scalars().all()

    # 결과 반환 (JobPosting 객체 리스트)
    return list(postings), total_count


async def get_popular_job_postings(
    session: AsyncSession, limit: int = 10
) -> tuple[list[JobPosting], int]:
    """인기 채용 공고 조회 (지원자 수 기준)"""
    # from sqlalchemy import func, desc # 상단으로 이동
    # from app.models.job_applications import JobApplication # 상단으로 이동

    # 지원자 수를 계산하는 서브쿼리
    applications_count_sq = (
        select(
            JobApplication.job_posting_id,
            func.count().label('app_count')
        )
        .group_by(JobApplication.job_posting_id)
        # .alias('app_counts')
        .subquery('app_counts') # subquery 사용
    )

    # 채용공고와 지원자 수를 조인하는 쿼리 (지원자가 없는 공고도 포함)
    list_query = (
        select(JobPosting)
        .outerjoin(applications_count_sq, JobPosting.id == applications_count_sq.c.job_posting_id)
        # .order_by(desc(applications_count.c.app_count), desc(JobPosting.created_at))
        .order_by(desc(func.coalesce(applications_count_sq.c.app_count, 0)), desc(JobPosting.created_at)) # 지원자 없으면 0으로 처리
        .limit(limit)
    )

    # 총 채용공고 수 조회 (필요 시)
    # count_query = select(func.count(1)).select_from(JobPosting)
    # total_count = await session.scalar(count_query)

    # 쿼리 실행 및 결과 반환
    result = await session.execute(list_query)
    postings = result.scalars().all()

    # 참고: 인기 목록은 전체 개수를 반환할 필요가 없을 수 있음 (상위 N개만 보여주므로)
    # 여기서는 일단 전체 공고 수를 반환 (기존 로직 유지)
    count_query = select(func.count(JobPosting.id))
    total_count = await session.scalar(count_query)

    return list(postings), total_count
