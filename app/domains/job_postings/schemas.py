from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.job_postings import (EducationEnum, JobCategoryEnum,
                                     PaymentMethodEnum, WorkDurationEnum)


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


class JobPostingUpdate(BaseModel):
    title: Optional[str]
    recruit_period_start: Optional[date]
    recruit_period_end: Optional[date]
    is_always_recruiting: Optional[bool]
    education: Optional[EducationEnum]
    recruit_number: Optional[int]
    benefits: Optional[str]
    preferred_conditions: Optional[str]
    other_conditions: Optional[str]
    work_address: Optional[str]
    work_place_name: Optional[str]
    payment_method: Optional[PaymentMethodEnum]
    job_category: Optional[JobCategoryEnum]
    work_duration: Optional[WorkDurationEnum]
    career: Optional[str]
    employment_type: Optional[str]
    salary: Optional[int]
    deadline_at: Optional[date]
    work_days: Optional[str]
    description: Optional[str]
    posings_image: Optional[str]
