from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from app.models.job_postings import (EducationEnum, JobCategoryEnum,
                                     PaymentMethodEnum, WorkDurationEnum)


class JobPostingBase(BaseModel):
    title: Optional[str] = None
    recruit_period_start: Optional[date] = None
    recruit_period_end: Optional[date] = None
    is_always_recruiting: Optional[bool] = None
    education: Optional[EducationEnum] = None
    recruit_number: Optional[int] = None  # 0은 "인원 미정" 또는 "수시" 의미
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
    recruit_number: int  # 0은 "인원 미정" 또는 "수시" 의미
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

    @model_validator(mode='after')
    def validate_dates(self) -> 'JobPostingCreate':
        """날짜 필드의 유효성 검증

        1. 모집 시작일은 종료일보다 이전이어야 함
        2. 모집 마감일은 시작일 이후이고 종료일 이전이어야 함
        3. 모집 기간(시작일~종료일)은 현재 날짜 이후여야 함(과거 날짜 금지)
        """
        # 항상 모집 중이 아닌 경우에만 날짜 검증
        if not self.is_always_recruiting:
            # 시작일이 종료일보다 나중인 경우
            if self.recruit_period_start > self.recruit_period_end:
                raise ValueError("모집 시작일은 종료일보다 빨라야 합니다")
            
            # 마감일이 시작일보다 빠른 경우
            if self.deadline_at < self.recruit_period_start:
                raise ValueError("모집 마감일은 시작일과 같거나 이후여야 합니다")
            
            # 마감일이 종료일보다 나중인 경우
            if self.deadline_at > self.recruit_period_end:
                raise ValueError("모집 마감일은 종료일과 같거나 이전이어야 합니다")
            
            # 현재 날짜가 시작일 이후인 경우 (과거 날짜 검증)
            today = date.today()
            if self.recruit_period_start < today:
                raise ValueError("모집 시작일은 현재 날짜 이후여야 합니다")
        
        return self
    
    @field_validator('salary')
    @classmethod
    def validate_salary(cls, v: int) -> int:
        """급여 필드 유효성 검증"""
        if v < 0:
            raise ValueError("급여는 0 이상이어야 합니다")
        return v


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
    
    @model_validator(mode='after')
    def validate_dates(self) -> 'JobPostingUpdate':
        """날짜 필드 업데이트 시 유효성 검증
        
        모든 필드가 선택적이기 때문에 존재하는 필드에 대해서만 검증 수행
        """
        # 시작일과 종료일이 모두 제공된 경우
        if self.recruit_period_start is not None and self.recruit_period_end is not None:
            if self.recruit_period_start > self.recruit_period_end:
                raise ValueError("모집 시작일은 종료일보다 빨라야 합니다")
        
        # 시작일과 마감일이 모두 제공된 경우
        if self.recruit_period_start is not None and self.deadline_at is not None:
            if self.deadline_at < self.recruit_period_start:
                raise ValueError("모집 마감일은 시작일과 같거나 이후여야 합니다")
        
        # 종료일과 마감일이 모두 제공된 경우
        if self.recruit_period_end is not None and self.deadline_at is not None:
            if self.deadline_at > self.recruit_period_end:
                raise ValueError("모집 마감일은 종료일과 같거나 이전이어야 합니다")
        
        # 시작일이 제공되고 현재 날짜보다 이전인 경우
        if self.recruit_period_start is not None:
            today = date.today()
            if self.recruit_period_start < today:
                raise ValueError("모집 시작일은 현재 날짜 이후여야 합니다")
        
        return self
    
    @field_validator('salary')
    @classmethod
    def validate_salary(cls, v: Optional[int]) -> Optional[int]:
        """급여 필드 유효성 검증 (선택적)"""
        if v is not None and v < 0:
            raise ValueError("급여는 0 이상이어야 합니다")
        return v


class PaginatedJobPostingResponse(BaseModel):
    items: list[JobPostingResponse]
    total: int
    skip: int
    limit: int
