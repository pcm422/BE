from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

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
    # 전체 채용공고 수 조회
    count_query = select(func.count()).select_from(JobPosting)
    total_count = await session.scalar(count_query)
    
    # 페이지네이션 적용한 채용공고 목록 조회
    result = await session.execute(
        select(JobPosting)
        .order_by(JobPosting.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    return result.scalars().all(), total_count


async def get_job_posting(
    session: AsyncSession, job_posting_id: int
) -> JobPosting | None:
    result = await session.execute(
        select(JobPosting).where(JobPosting.id == job_posting_id)
    )
    return result.scalars().first()


async def update_job_posting(
    session: AsyncSession, job_posting_id: int, data: JobPostingUpdate
) -> JobPosting | None:
    result = await session.execute(
        select(JobPosting).where(JobPosting.id == job_posting_id)
    )
    job_posting = result.scalars().first()
    if not job_posting:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job_posting, key, value)

    await session.commit()
    await session.refresh(job_posting)
    return job_posting


async def delete_job_posting(
    session: AsyncSession, job_posting_id: int
) -> JobPosting | None:
    result = await session.execute(
        select(JobPosting).where(JobPosting.id == job_posting_id)
    )
    job_posting = result.scalars().first()
    if not job_posting:
        return None

    await session.delete(job_posting)
    await session.commit()
    return job_posting
