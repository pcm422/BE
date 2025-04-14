from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.job_postings import (EducationEnum, JobCategoryEnum,
                                     PaymentMethodEnum, WorkDurationEnum)


class JobPostingBase(BaseModel):
    title: Optional[str] = None
    recruit_period_start: Optional[date] = None
    recruit_period_end: Optional[date] = None
    is_always_recruiting: Optional[bool] = None
    education: Optional[EducationEnum] = None
    recruit_number: Optional[int] = None
    benefits: Optional[str] = None
    preferred_conditions: Optional[str] = None
    other_conditions: Optional[str] = None
    work_address: Optional[str] = None
    work_place_name: Optional[str] = None
    payment_method: Optional[PaymentMethodEnum] = None
    job_category: Optional[JobCategoryEnum] = None
    work_duration: Optional[WorkDurationEnum] = None
    career: Optional[str] = None
    employment_type: Optional[str] = None
    salary: Optional[int] = None
    deadline_at: Optional[date] = None
    work_days: Optional[str] = None
    description: Optional[str] = None
    posings_image: Optional[str] = None


class JobPostingCreate(JobPostingBase):
    title: str
    recruit_period_start: date
    recruit_period_end: date
    is_always_recruiting: bool
    education: EducationEnum
    recruit_number: int
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


class JobPostingResponse(JobPostingBase):
    id: int
    author_id: int
    company_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class JobPostingUpdate(JobPostingBase):
    pass


class PaginatedJobPostingResponse(BaseModel):
    items: List[JobPostingResponse]
    total: int
    skip: int
    limit: int
