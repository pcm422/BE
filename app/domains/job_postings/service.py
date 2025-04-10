from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.job_postings import JobPosting
from app.domains.job_postings.schemas import JobPostingCreate

async def create_job_posting(
    session: AsyncSession,
    data: JobPostingCreate,
    author_id: int,
    company_id: int
) -> JobPosting:
    job_posting = JobPosting(
        **data.model_dump(),
        author_id=author_id,
        company_id=company_id
    )
    session.add(job_posting)
    await session.commit()
    await session.refresh(job_posting)
    return job_posting
