from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from sqlalchemy.orm import selectinload

from app.domains.job_postings.schemas import JobPostingCreate, JobPostingUpdate
from app.models.job_postings import JobPosting


async def create_job_posting(
    session: AsyncSession, data: JobPostingCreate, author_id: int, company_id: int
) -> JobPosting:
    job_posting = JobPosting(
        **data.model_dump(), author_id=author_id, company_id=company_id
    )
    session.add(job_posting)
    await session.commit()
    await session.refresh(job_posting)
    return job_posting


async def list_job_postings(
    session: AsyncSession, skip: int = 0, limit: int = 10
) -> tuple[list[JobPosting], int]:
    # 목록 조회에 필요한 필드만 선택 (성능 최적화)
    list_columns = [
        JobPosting.id,
        JobPosting.title,
        JobPosting.job_category,
        JobPosting.work_address,
        JobPosting.salary,
        JobPosting.recruit_period_start,
        JobPosting.recruit_period_end,
        JobPosting.deadline_at,
        JobPosting.is_always_recruiting,
        JobPosting.created_at,
        JobPosting.updated_at,
        JobPosting.author_id,
        JobPosting.company_id,
    ]
    
    # 검색 조건이 없는 기본 쿼리
    base_query = select(*list_columns).select_from(JobPosting)
    
    # 카운트 쿼리 (위치 평가식을 사용하여 카운트)
    count_query = select(func.count(1)).select_from(JobPosting)
    
    # 카운트 실행 (최적화된 카운트 쿼리)
    total_count = await session.scalar(count_query)
    
    # 정렬 및 페이지네이션 적용
    query = base_query.order_by(desc(JobPosting.created_at)).offset(skip).limit(limit)
    
    # 최종 쿼리 실행
    result = await session.execute(query)
    
    # 결과 반환 (성능을 위해 목록 조회에 필요한 필드만 포함)
    return list(result.all()), total_count


async def get_job_posting(
    session: AsyncSession, job_posting_id: int
) -> JobPosting | None:
    # 상세 조회는 전체 필드를 가져오되, 캐시를 활용하기 위한 옵션 추가
    result = await session.execute(
        select(JobPosting)
        .where(JobPosting.id == job_posting_id)
        .execution_options(populate_existing=True)
    )
    return result.scalars().first()


async def update_job_posting(
    session: AsyncSession, job_posting_id: int, data: JobPostingUpdate
) -> JobPosting | None:
    # 최적화: 단일 쿼리로 데이터 가져오기
    job_posting = await get_job_posting(session, job_posting_id)
    if not job_posting:
        return None

    # 변경된 필드만 업데이트하여 DB 부하 최소화
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:  # 업데이트할 데이터가 없으면 조기 반환
        return job_posting
        
    for key, value in update_data.items():
        setattr(job_posting, key, value)

    # 트랜잭션 최적화
    await session.commit()
    await session.refresh(job_posting)
    return job_posting


async def delete_job_posting(
    session: AsyncSession, job_posting_id: int
) -> JobPosting | None:
    # 기존 get_job_posting 함수 재사용
    job_posting = await get_job_posting(session, job_posting_id)
    if not job_posting:
        return None

    await session.delete(job_posting)
    await session.commit()
    return job_posting


async def search_job_postings(
    session: AsyncSession,
    keyword: str | None = None,
    location: str | None = None,
    job_category: str | None = None,
    employment_type: str | None = None,
    is_always_recruiting: bool | None = None,
    page: int = 1,
    limit: int = 10,
    sort: str = "latest"
) -> tuple[list[JobPosting], int]:
    # 목록 조회에 필요한 필드만 선택 (성능 최적화)
    list_columns = [
        JobPosting.id,
        JobPosting.title,
        JobPosting.job_category,
        JobPosting.work_address,
        JobPosting.salary,
        JobPosting.recruit_period_start,
        JobPosting.recruit_period_end,
        JobPosting.deadline_at,
        JobPosting.is_always_recruiting,
        JobPosting.created_at,
        JobPosting.updated_at,
        JobPosting.author_id,
        JobPosting.company_id,
    ]
    
    # 기본 쿼리
    base_query = select(*list_columns).select_from(JobPosting)
    
    # 검색 조건 적용
    if keyword:
        base_query = base_query.where(
            JobPosting.title.ilike(f"%{keyword}%") | 
            JobPosting.description.ilike(f"%{keyword}%")
        )
    
    if location:
        base_query = base_query.where(JobPosting.work_address.ilike(f"%{location}%"))
    
    if job_category:
        base_query = base_query.where(JobPosting.job_category == job_category)
    
    if employment_type:
        base_query = base_query.where(JobPosting.employment_type == employment_type)
    
    if is_always_recruiting is not None:
        base_query = base_query.where(JobPosting.is_always_recruiting == is_always_recruiting)
    
    # 카운트 쿼리 (동일한 필터 적용)
    count_query = select(func.count(1)).select_from(
        base_query.alias("filtered_postings")
    )
    
    # 정렬 적용
    if sort == "latest":
        base_query = base_query.order_by(desc(JobPosting.created_at))
    elif sort == "deadline":
        base_query = base_query.order_by(JobPosting.deadline_at)
    elif sort == "salary_high":
        base_query = base_query.order_by(desc(JobPosting.salary))
    elif sort == "salary_low":
        base_query = base_query.order_by(JobPosting.salary)
    
    # 페이지네이션 적용
    skip = (page - 1) * limit
    base_query = base_query.offset(skip).limit(limit)
    
    # 쿼리 실행
    result = await session.execute(base_query)
    total_count = await session.scalar(count_query)
    
    # 결과 반환
    return list(result.all()), total_count
