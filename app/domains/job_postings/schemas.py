from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

from app.models.job_postings import (
    EducationEnum,
    PaymentMethodEnum,
    JobCategoryEnum,
    WorkDurationEnum
)

class JobPostingCreate(BaseModel):
    title: str
    recruit_period_start: date
    recruit_period_end: date
    is_always_recruiting: bool
    education: EducationEnum
    recruit_number: int
    benefits: Optional[str]
    preferred_conditions: Optional[str]
    other_conditions: Optional[str]
    work_address: str
    work_place_name: str
    payment_method: PaymentMethodEnum
    job_category: JobCategoryEnum
    work_duration: WorkDurationEnum
    career: str
    employment_type: str
    salary: int
    deadline_at: date
    work_days: str
    description: str
    posings_image: str


class JobPostingResponse(JobPostingCreate):
    id: int
    author_id: int
    company_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True