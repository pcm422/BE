from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc

from app.domains.job_postings.schemas import JobPostingUpdate, JobPostingCreateWithImage
from app.models.job_postings import JobPosting
from app.core.utils import upload_image_to_ncp
from fastapi import UploadFile


async def create_job_posting(
    session: AsyncSession, data: JobPostingCreateWithImage, author_id: int, company_id: int, image_file: UploadFile = None
) -> JobPosting:
    # 이미지 업로드 (있을 경우)
    image_url = None
    try:
        if image_file:
            image_url = await upload_image_to_ncp(image_file, folder="job_postings")
    except Exception as e:
        # 이미지 업로드 실패 시 로깅 및 계속 진행 (이미지 없이)
        print(f"이미지 업로드 실패: {e}")
    
    # data에서 author_id와 company_id를 제외한 데이터 추출
    data_dict = data.model_dump(exclude={"author_id", "company_id"})
    
    # 새 JobPosting 객체 생성 (이미 모든 형변환은 스키마에서 처리됨)
    job_posting = JobPosting(
        **data_dict, 
        author_id=author_id, 
        company_id=company_id, 
        posings_image=image_url
    )
    
    try:
        session.add(job_posting)
        await session.commit()
        await session.refresh(job_posting)
        return job_posting
    except Exception as e:
        await session.rollback()
        raise e


async def list_job_postings(
    session: AsyncSession, skip: int = 0, limit: int = 10
) -> tuple[list[JobPosting], int]:
    # ORM 객체를 직접 반환하도록 수정
    base_query = select(JobPosting)
    
    # 카운트 쿼리 (위치 평가식을 사용하여 카운트)
    count_query = select(func.count(1)).select_from(JobPosting)
    
    # 카운트 실행 (최적화된 카운트 쿼리)
    total_count = await session.scalar(count_query)
    
    # 정렬 및 페이지네이션 적용
    query = base_query.order_by(desc(JobPosting.created_at)).offset(skip).limit(limit)
    
    # 최종 쿼리 실행 - scalars()를 사용하여 ORM 객체 반환
    result = await session.execute(query)
    
    # 결과 반환 (JobPosting 객체 리스트)
    return list(result.scalars().all()), total_count


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
    # ORM 객체를 직접 반환하도록 수정
    base_query = select(JobPosting)
    
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
    
    # 쿼리 실행 - scalars()를 사용하여 ORM 객체 반환
    result = await session.execute(base_query)
    total_count = await session.scalar(count_query)
    
    # 결과 반환 (JobPosting 객체 리스트)
    return list(result.scalars().all()), total_count


async def get_popular_job_postings(
    session: AsyncSession, limit: int = 10
) -> tuple[list[JobPosting], int]:
    """
    인기 채용 정보를 조회하는 함수
    
    지원자 수가 많은 순으로 채용 정보를 정렬하여 반환
    
    Args:
        session: DB 세션
        limit: 조회할 개수
        
    Returns:
        인기 채용 정보(JobPosting 객체) 목록과 총 개수를 반환
    """
    from sqlalchemy import func, desc
    from app.models.job_applications import JobApplication
    
    # 지원자 수를 계산하는 서브쿼리
    applications_count = (
        select(JobApplication.job_posting_id, func.count().label('app_count'))
        .group_by(JobApplication.job_posting_id)
        .alias('app_counts')
    )
    
    # 채용공고 객체와 지원자 수를 조인하는 쿼리
    base_query = (
        select(JobPosting)
        .outerjoin(applications_count, JobPosting.id == applications_count.c.job_posting_id)
        .order_by(desc(applications_count.c.app_count), desc(JobPosting.created_at))
        .limit(limit)
    )
    
    # 총 채용공고 수 조회
    count_query = select(func.count(1)).select_from(JobPosting)
    total_count = await session.scalar(count_query)
    
    # 쿼리 실행 및 결과 반환
    result = await session.execute(base_query)
    postings = result.scalars().all()
    
    return list(postings), total_count
