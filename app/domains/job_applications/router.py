from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.utils import get_current_company_user
from app.domains.job_applications.schemas import JobApplicationRead, JobApplicationCreate, JobApplicationStatusUpdate
from app.domains.job_applications.service import create_application, get_user_applications, delete_application
from app.domains.users.router import read_current_user

router = APIRouter(prefix="/applications", tags=["지원내역"])


@router.post("/", response_model=JobApplicationRead, status_code=status.HTTP_201_CREATED)
async def apply_job(
    payload: JobApplicationCreate,
    db: AsyncSession = Depends(get_db_session),
    user=Depends(read_current_user)
):
    result = await create_application(user.id, payload.job_posting_id, db)
    return result


@router.get("/", response_model=list[JobApplicationRead])
async def read_my_applications(
    db: AsyncSession = Depends(get_db_session),
    user=Depends(read_current_user)
):
    result = await get_user_applications(user.id, db)
    return result


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_application(
    application_id: int,
    db: AsyncSession = Depends(get_db_session),
    user=Depends(read_current_user)
):
    result = await delete_application(application_id, user.id, db)
    await result


@router.patch("/{application_id}/status", response_model=JobApplicationRead)
async def update_application_status(
    application_id: int,
    payload: JobApplicationStatusUpdate,
    db: AsyncSession = Depends(get_db_session),
    company_user=Depends(get_current_company_user)
):
    # 인증된 기업 담당자만 상태 변경 가능
    result = await update_application_status(application_id=application_id,
        status=payload.status,
        session=db)
    return result