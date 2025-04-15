from pydantic import BaseModel, Field
from datetime import datetime

from app.models.job_applications import ApplicationStatusEnum

class JobApplicationCreate(BaseModel):
    job_posting_id: int = Field(..., description="지원할 공고 ID")


class JobApplicationRead(BaseModel):
    id: int
    job_posting_id: int
    status: ApplicationStatusEnum
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class JobApplicationStatusUpdate(BaseModel):
    status: ApplicationStatusEnum = Field(..., description="새로운 지원 상태")
    