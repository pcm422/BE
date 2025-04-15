from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models import JobApplication
from app.models.job_applications import ApplicationStatusEnum


async def create_application(user_id: int, job_posting_id: int, session: AsyncSession):
    """채용 공고에 지원"""
    application = JobApplication(user_id=user_id, job_posting_id=job_posting_id)
    session.add(application)
    try:
        await session.commit()
        await session.refresh(application)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="이미 지원한 공고입니다.")
    return application


async def get_user_applications(user_id: int, session: AsyncSession):
    """해당 유저의 전체 지원 내역 조회"""
    result = await session.execute(
        select(JobApplication).where(JobApplication.user_id == user_id)
    )
    return result.scalars().all()


async def delete_application(application_id: int, user_id: int, session: AsyncSession):
    """해당 유저의 지원 내역 삭제"""
    result = await session.execute(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == user_id
        )
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="지원 내역을 찾을 수 없습니다.")
    await session.delete(application)
    await session.commit()


async def update_application_status(
    application_id: int,
    status: ApplicationStatusEnum,
    session: AsyncSession
):
    """기업담당자가 지원 상태 변경"""
    result = await session.execute(
        select(JobApplication).where(JobApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="지원 내역이 없습니다.")
    application.status = status
    await session.commit()
    await session.refresh(application)
    return application