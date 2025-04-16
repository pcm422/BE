from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from fastapi import Form
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
    
    @classmethod
    def as_form(
        cls,
        title: str = Form(..., description="채용공고 제목"),
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
        # 문자열 날짜를 date 객체로 변환 (예외 처리 추가)
        start_date = None
        end_date = None
        deadline = None
        
        try:
            if recruit_period_start:
                start_date = date.fromisoformat(recruit_period_start)
        except ValueError:
            raise ValueError("모집 시작일 형식이 올바르지 않습니다 (YYYY-MM-DD)")
            
        try:
            if recruit_period_end:
                end_date = date.fromisoformat(recruit_period_end)
        except ValueError:
            raise ValueError("모집 종료일 형식이 올바르지 않습니다 (YYYY-MM-DD)")
            
        try:
            if deadline_at:
                deadline = date.fromisoformat(deadline_at)
        except ValueError:
            raise ValueError("마감일 형식이 올바르지 않습니다 (YYYY-MM-DD)")
        
        # 문자열을 적절한 타입으로 변환
        recruit_number_int = None
        if recruit_number:
            try:
                recruit_number_int = int(recruit_number)
            except ValueError:
                raise ValueError("모집 인원은 숫자여야 합니다")
        
        salary_int = None
        if salary:
            try:
                salary_int = int(salary)
                if salary_int < 0:
                    raise ValueError("급여는 0 이상이어야 합니다")
            except ValueError as e:
                if "급여는 0 이상이어야 합니다" in str(e):
                    raise e
                raise ValueError("급여는 숫자여야 합니다")
        
        # Enum 변환
        education_enum = None
        if education:
            try:
                education_enum = EducationEnum[education]
            except KeyError:
                # 값이 Enum 값과 일치하는 경우 (enum.value)
                for enum_member in EducationEnum:
                    if enum_member.value == education:
                        education_enum = enum_member
                        break
                else:
                    raise ValueError(f"유효하지 않은 학력 값: {education}")
        
        payment_method_enum = None
        if payment_method:
            try:
                payment_method_enum = PaymentMethodEnum[payment_method]
            except KeyError:
                # 값이 Enum 값과 일치하는 경우 (enum.value)
                for enum_member in PaymentMethodEnum:
                    if enum_member.value == payment_method:
                        payment_method_enum = enum_member
                        break
                else:
                    raise ValueError(f"유효하지 않은 지불 방식 값: {payment_method}")
        
        job_category_enum = None
        if job_category:
            try:
                job_category_enum = JobCategoryEnum[job_category]
            except KeyError:
                # 값이 Enum 값과 일치하는 경우 (enum.value)
                for enum_member in JobCategoryEnum:
                    if enum_member.value == job_category:
                        job_category_enum = enum_member
                        break
                else:
                    raise ValueError(f"유효하지 않은 직종 카테고리 값: {job_category}")
        
        work_duration_enum = None
        if work_duration:
            try:
                work_duration_enum = WorkDurationEnum[work_duration]
            except KeyError:
                # 값이 Enum 값과 일치하는 경우 (enum.value)
                for enum_member in WorkDurationEnum:
                    if enum_member.value == work_duration:
                        work_duration_enum = enum_member
                        break
                else:
                    raise ValueError(f"유효하지 않은 근무 기간 값: {work_duration}")
        
        # author_id와 company_id는 라우터에서 current_user로부터 설정되므로 0으로 임시 설정
        return cls(
            title=title,
            author_id=0,  # 임시값, 라우터에서 덮어씀
            company_id=0,  # 임시값, 라우터에서 덮어씀
            recruit_period_start=start_date,
            recruit_period_end=end_date,
            is_always_recruiting=is_always_recruiting,
            education=education_enum,
            recruit_number=recruit_number_int,
            benefits=benefits,
            preferred_conditions=preferred_conditions,
            other_conditions=other_conditions,
            work_address=work_address,
            work_place_name=work_place_name,
            payment_method=payment_method_enum,
            job_category=job_category_enum,
            work_duration=work_duration_enum,
            career=career,
            employment_type=employment_type,
            salary=salary_int,
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
