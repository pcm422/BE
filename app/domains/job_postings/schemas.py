from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from fastapi import UploadFile, Form, File
from typing import Optional
import json

from app.models.job_postings import (EducationEnum, JobCategoryEnum,
                                     PaymentMethodEnum, WorkDurationEnum)


class JobPostingBase(BaseModel):
    title: str | None = None
    recruit_period_start: date | None = None
    recruit_period_end: date | None = None
    is_always_recruiting: bool | None = None
    education: EducationEnum | None = None
    recruit_number: int | None = None  # 0은 "인원 미정" 또는 "수시" 의미
    benefits: str | None = None
    preferred_conditions: str | None = None
    other_conditions: str | None = None
    work_address: str | None = None
    work_place_name: str | None = None
    payment_method: PaymentMethodEnum | None = None
    job_category: JobCategoryEnum | None = None
    work_duration: WorkDurationEnum | None = None
    career: str | None = None
    employment_type: str | None = None
    salary: int | None = None
    deadline_at: date | None = None
    work_days: str | None = None
    description: str | None = None
    posings_image: str | None = None


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

    model_config = ConfigDict(from_attributes=True)


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
    def validate_salary(cls, v: int | None) -> int | None:
        """급여 필드 유효성 검증 (선택적)"""
        if v is not None and v < 0:
            raise ValueError("급여는 0 이상이어야 합니다")
        return v


class PaginatedJobPostingResponse(BaseModel):
    items: list[JobPostingResponse]
    total: int
    skip: int
    limit: int


class JobPostingCreateWithImage(BaseModel):
    title: str
    author_id: int
    company_id: int
    recruit_period_start: Optional[date] = None
    recruit_period_end: Optional[date] = None
    is_always_recruiting: bool = False
    education: Optional[str] = None
    recruit_number: Optional[str] = None
    benefits: Optional[str] = None
    preferred_conditions: Optional[str] = None
    other_conditions: Optional[str] = None
    work_address: Optional[str] = None
    work_place_name: Optional[str] = None
    payment_method: Optional[str] = None
    job_category: Optional[str] = None
    work_duration: Optional[str] = None
    career: Optional[str] = None
    employment_type: Optional[str] = None
    salary: Optional[str] = None
    deadline_at: Optional[datetime] = None
    work_days: Optional[str] = None
    description: Optional[str] = None
    
    @classmethod
    def as_form(
        cls,
        title: str = Form(..., description="채용공고 제목"),
        author_id: int = Form(..., description="작성자 ID"),
        company_id: int = Form(..., description="회사 ID"),
        recruit_period_start: Optional[str] = Form(None, description="모집 시작일 (YYYY-MM-DD)"),
        recruit_period_end: Optional[str] = Form(None, description="모집 종료일 (YYYY-MM-DD)"),
        is_always_recruiting: bool = Form(False, description="상시 모집 여부"),
        education: Optional[str] = Form(None, description="요구 학력 (none, high, college_2, college_4, graduate)"),
        recruit_number: Optional[str] = Form(None, description="모집 인원 (숫자)"),
        benefits: Optional[str] = Form(None, description="복리 후생"),
        preferred_conditions: Optional[str] = Form(None, description="우대 조건"),
        other_conditions: Optional[str] = Form(None, description="기타 조건"),
        work_address: Optional[str] = Form(None, description="근무지 주소"),
        work_place_name: Optional[str] = Form(None, description="근무지명"),
        payment_method: Optional[str] = Form(None, description="급여 지급 방식 (hourly, daily, weekly, monthly, yearly)"),
        job_category: Optional[str] = Form(None, description="직종 카테고리"),
        work_duration: Optional[str] = Form(None, description="근무 기간"),
        career: Optional[str] = Form(None, description="경력 요구사항"),
        employment_type: Optional[str] = Form(None, description="고용 형태"),
        salary: Optional[str] = Form(None, description="급여 (숫자)"),
        deadline_at: Optional[str] = Form(None, description="마감일 (YYYY-MM-DD)"),
        work_days: Optional[str] = Form(None, description="근무 요일/스케줄"),
        description: Optional[str] = Form(None, description="상세 설명"),
    ):
        # 문자열 날짜를 date 객체로 변환
        start_date = date.fromisoformat(recruit_period_start) if recruit_period_start else None
        end_date = date.fromisoformat(recruit_period_end) if recruit_period_end else None
        deadline = datetime.fromisoformat(deadline_at) if deadline_at else None
        
        return cls(
            title=title,
            author_id=author_id,
            company_id=company_id,
            recruit_period_start=start_date,
            recruit_period_end=end_date,
            is_always_recruiting=is_always_recruiting,
            education=education,
            recruit_number=recruit_number,
            benefits=benefits,
            preferred_conditions=preferred_conditions,
            other_conditions=other_conditions,
            work_address=work_address,
            work_place_name=work_place_name,
            payment_method=payment_method,
            job_category=job_category,
            work_duration=work_duration,
            career=career,
            employment_type=employment_type,
            salary=salary,
            deadline_at=deadline,
            work_days=work_days,
            description=description,
        )


class JobPostingHelpers(BaseModel):
    @staticmethod
    def get_education_options():
        """학력 옵션 목록 반환"""
        return [{"value": edu.value, "label": edu.value} for edu in EducationEnum]
    
    @staticmethod
    def get_payment_method_options():
        """급여 지급 방식 옵션 목록 반환"""
        return [{"value": method.value, "label": method.value} for method in PaymentMethodEnum]
    
    @staticmethod
    def get_job_category_options():
        """직종 카테고리 옵션 목록 반환"""
        return [{"value": cat.value, "label": cat.value} for cat in JobCategoryEnum]
    
    @staticmethod
    def get_work_duration_options():
        """근무 기간 옵션 목록 반환"""
        return [{"value": dur.value, "label": dur.value} for dur in WorkDurationEnum]
