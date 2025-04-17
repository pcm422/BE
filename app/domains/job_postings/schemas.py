import enum
from datetime import date, datetime
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field
from fastapi import Form, HTTPException, status
from typing import Optional

from app.models.job_postings import (EducationEnum, JobCategoryEnum,
                                     PaymentMethodEnum, WorkDurationEnum)

TEnum = TypeVar("TEnum", bound=enum.Enum)

# --- Helper Functions ---

def _validate_dates_logic(start_date: date | None, end_date: date | None, deadline: date | None, is_always_recruiting: bool | None) -> None:
    """공통 날짜 유효성 검사 로직"""
    if not is_always_recruiting:
        today = date.today()

        # 시작일과 종료일 관계 검증 (둘 다 존재할 때)
        if start_date and end_date and start_date > end_date:
            raise ValueError("모집 시작일은 종료일보다 빨라야 합니다")

        # 마감일과 시작일 관계 검증 (둘 다 존재할 때)
        if deadline and start_date and deadline < start_date:
             raise ValueError("모집 마감일은 시작일과 같거나 이후여야 합니다")

        # 마감일과 종료일 관계 검증 (둘 다 존재할 때)
        if deadline and end_date and deadline > end_date:
            raise ValueError("모집 마감일은 종료일과 같거나 이전이어야 합니다")

        # 시작일이 과거인지 검증 (시작일이 존재할 때)
        if start_date and start_date < today:
            raise ValueError("모집 시작일은 현재 날짜 이후여야 합니다")

def _parse_date(date_str: str | None, field_name: str) -> date | None:
    """문자열을 날짜 객체로 변환"""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(f"{field_name} 형식이 올바르지 않습니다 (YYYY-MM-DD)")

def _parse_int(int_str: str | None, field_name: str, min_value: int | None = None) -> int | None:
    """문자열을 정수 객체로 변환하고 최소값 검증"""
    if int_str is None:
        return None
    try:
        value = int(int_str)
        if min_value is not None and value < min_value:
            raise ValueError(f"{field_name}은(는) {min_value} 이상이어야 합니다")
        return value
    except ValueError as e:
        # 이미 최소값 에러가 발생한 경우 해당 에러를 그대로 전달
        if min_value is not None and str(min_value) in str(e):
             raise e
        raise ValueError(f"{field_name}은(는) 숫자여야 합니다")


def _parse_enum(enum_class: Type[TEnum], value: str | None, field_name: str) -> TEnum | None:
    """문자열을 Enum 객체로 변환 (key 또는 value로 검색)"""
    if value is None:
        return None
    try:
        # Enum 키(멤버 이름)로 찾기 시도
        return enum_class[value]
    except KeyError:
        # Enum 값으로 찾기 시도
        for member in enum_class:
            if member.value == value:
                return member
        # 둘 다 실패하면 에러 발생
        valid_options = ", ".join([m.name for m in enum_class]) + " 또는 " + ", ".join([m.value for m in enum_class])
        raise ValueError(f"유효하지 않은 {field_name} 값: {value}. 가능한 값: {valid_options}")


# --- Pydantic Schemas ---

class JobPostingBase(BaseModel):
    title: str | None = Field(None, description="채용공고 제목")
    recruit_period_start: date | None = Field(None, description="모집 시작일")
    recruit_period_end: date | None = Field(None, description="모집 종료일")
    is_always_recruiting: bool | None = Field(False, description="상시 모집 여부")
    education: EducationEnum | None = Field(None, description="요구 학력")
    recruit_number: int | None = Field(None, description="모집 인원 (0은 '인원 미정')")
    benefits: str | None = Field(None, description="복리 후생")
    preferred_conditions: str | None = Field(None, description="우대 조건")
    other_conditions: str | None = Field(None, description="기타 조건")
    work_address: str | None = Field(None, description="근무지 주소")
    work_place_name: str | None = Field(None, description="근무지명")
    payment_method: PaymentMethodEnum | None = Field(None, description="급여 지급 방식")
    job_category: JobCategoryEnum | None = Field(None, description="직종 카테고리")
    work_duration: WorkDurationEnum | None = Field(None, description="근무 기간")
    career: str | None = Field(None, description="경력 요구사항")
    employment_type: str | None = Field(None, description="고용 형태")
    salary: int | None = Field(None, description="급여")
    deadline_at: date | None = Field(None, description="마감일")
    work_days: str | None = Field(None, description="근무 요일/스케줄")
    description: str | None = Field(None, description="상세 설명")
    postings_image: str | None = Field(None, description="공고 이미지 URL")

    model_config = ConfigDict(from_attributes=True) # ORM 모델과 매핑 활성화


class JobPostingCreate(JobPostingBase):
    # Create 시에는 대부분의 필드가 필수이므로 재정의
    title: str = Field(..., description="채용공고 제목")
    recruit_period_start: date = Field(..., description="모집 시작일")
    recruit_period_end: date = Field(..., description="모집 종료일")
    is_always_recruiting: bool = Field(False, description="상시 모집 여부")
    education: EducationEnum = Field(..., description="요구 학력")
    recruit_number: int = Field(..., description="모집 인원 (0은 '인원 미정')")
    work_address: str = Field(..., description="근무지 주소")
    work_place_name: str = Field(..., description="근무지명")
    payment_method: PaymentMethodEnum = Field(..., description="급여 지급 방식")
    job_category: JobCategoryEnum = Field(..., description="직종 카테고리")
    work_duration: WorkDurationEnum = Field(..., description="근무 기간")
    career: str = Field(..., description="경력 요구사항")
    employment_type: str = Field(..., description="고용 형태")
    salary: int = Field(..., description="급여")
    deadline_at: date = Field(..., description="마감일")
    work_days: str = Field(..., description="근무 요일/스케줄")
    description: str = Field(..., description="상세 설명")
    postings_image: str | None = Field(None, description="공고 이미지 URL (선택)") # 이미지는 생성 시 필수가 아닐 수 있음

    @model_validator(mode='after')
    def validate_model(self) -> 'JobPostingCreate':
        """모델 레벨 유효성 검사 (날짜 검증 포함)"""
        try:
            _validate_dates_logic(
                self.recruit_period_start,
                self.recruit_period_end,
                self.deadline_at,
                self.is_always_recruiting
            )
        except ValueError as e:
             # Pydantic v2에서는 model_validator에서 ValueError 발생 시 자동으로 에러 처리
             # 하지만 명시적으로 HTTP 예외를 발생시키려면 아래와 같이 사용 가능
             # raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
             raise e # ValueError를 그대로 전달하여 Pydantic이 처리하도록 함
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
    # model_config은 Base에서 상속받음


class JobPostingUpdate(JobPostingBase):
    # Update 시에는 모든 필드가 선택적이므로 Base의 Optional 타입을 그대로 사용
    # 추가적인 필드 제약이 필요하면 여기에 정의

    @model_validator(mode='after')
    def validate_model(self) -> 'JobPostingUpdate':
        """모델 레벨 유효성 검사 (날짜 검증 포함, Optional 필드 고려)"""
        # Update 시에는 필드가 None일 수 있으므로, 있는 값들만 검증
        try:
            _validate_dates_logic(
                self.recruit_period_start,
                self.recruit_period_end,
                self.deadline_at,
                self.is_always_recruiting
            )
        except ValueError as e:
             raise e # ValueError를 그대로 전달
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


class JobPostingCreateFormData:
    """
    Form 데이터 처리를 위한 클래스 (Pydantic 모델 아님).
    FastAPI의 Depends와 함께 사용하여 Form 필드를 직접 주입받습니다.
    """
    def __init__(
        self,
        title: str = Form(..., description="채용공고 제목"),
        recruit_period_start: Optional[str] = Form(None, description="모집 시작일 (YYYY-MM-DD)"),
        recruit_period_end: Optional[str] = Form(None, description="모집 종료일 (YYYY-MM-DD)"),
        is_always_recruiting: bool = Form(False, description="상시 모집 여부"),
        education: Optional[str] = Form(None, description=f"요구 학력 (가능한 값: {', '.join([e.name for e in EducationEnum])} 또는 {', '.join([e.value for e in EducationEnum])})"),
        recruit_number: Optional[str] = Form(None, description="모집 인원 (숫자, 0은 '인원 미정')"),
        benefits: Optional[str] = Form(None, description="복리 후생"),
        preferred_conditions: Optional[str] = Form(None, description="우대 조건"),
        other_conditions: Optional[str] = Form(None, description="기타 조건"),
        work_address: Optional[str] = Form(None, description="근무지 주소"),
        work_place_name: Optional[str] = Form(None, description="근무지명"),
        payment_method: Optional[str] = Form(None, description=f"급여 지급 방식 (가능한 값: {', '.join([e.name for e in PaymentMethodEnum])} 또는 {', '.join([e.value for e in PaymentMethodEnum])})"),
        job_category: Optional[str] = Form(None, description=f"직종 카테고리 (가능한 값: {', '.join([e.name for e in JobCategoryEnum])} 또는 {', '.join([e.value for e in JobCategoryEnum])})"),
        work_duration: Optional[str] = Form(None, description=f"근무 기간 (가능한 값: {', '.join([e.name for e in WorkDurationEnum])} 또는 {', '.join([e.value for e in WorkDurationEnum])})"),
        career: Optional[str] = Form(None, description="경력 요구사항"),
        employment_type: Optional[str] = Form(None, description="고용 형태"),
        salary: Optional[str] = Form(None, description="급여 (숫자)"),
        deadline_at: Optional[str] = Form(None, description="마감일 (YYYY-MM-DD)"),
        work_days: Optional[str] = Form(None, description="근무 요일/스케줄"),
        description: Optional[str] = Form(None, description="상세 설명"),
    ):
        self.title = title
        self.recruit_period_start = recruit_period_start
        self.recruit_period_end = recruit_period_end
        self.is_always_recruiting = is_always_recruiting
        self.education = education
        self.recruit_number = recruit_number
        self.benefits = benefits
        self.preferred_conditions = preferred_conditions
        self.other_conditions = other_conditions
        self.work_address = work_address
        self.work_place_name = work_place_name
        self.payment_method = payment_method
        self.job_category = job_category
        self.work_duration = work_duration
        self.career = career
        self.employment_type = employment_type
        self.salary = salary
        self.deadline_at = deadline_at
        self.work_days = work_days
        self.description = description


    def parse_to_job_posting_create(self, postings_image_url: str | None) -> 'JobPostingCreate':
        """Form 데이터를 JobPostingCreate 모델로 변환하고 유효성 검사 수행"""
        try:
            start_date = _parse_date(self.recruit_period_start, "모집 시작일")
            end_date = _parse_date(self.recruit_period_end, "모집 종료일")
            deadline = _parse_date(self.deadline_at, "마감일")

            recruit_number_int = _parse_int(self.recruit_number, "모집 인원")
            salary_int = _parse_int(self.salary, "급여", min_value=0)

            education_enum = _parse_enum(EducationEnum, self.education, "학력")
            payment_method_enum = _parse_enum(PaymentMethodEnum, self.payment_method, "지불 방식")
            job_category_enum = _parse_enum(JobCategoryEnum, self.job_category, "직종 카테고리")
            work_duration_enum = _parse_enum(WorkDurationEnum, self.work_duration, "근무 기간")

            # JobPostingCreate 모델 생성 시 Pydantic 유효성 검사가 자동으로 실행됨
            # 필수 필드가 None이거나 잘못된 값이면 여기서 에러 발생
            create_data = {
                "title": self.title,
                "recruit_period_start": start_date,
                "recruit_period_end": end_date,
                "is_always_recruiting": self.is_always_recruiting,
                "education": education_enum,
                "recruit_number": recruit_number_int,
                "benefits": self.benefits,
                "preferred_conditions": self.preferred_conditions,
                "other_conditions": self.other_conditions,
                "work_address": self.work_address,
                "work_place_name": self.work_place_name,
                "payment_method": payment_method_enum,
                "job_category": job_category_enum,
                "work_duration": work_duration_enum,
                "career": self.career,
                "employment_type": self.employment_type,
                "salary": salary_int,
                "deadline_at": deadline,
                "work_days": self.work_days,
                "description": self.description,
                "postings_image": postings_image_url # 이미지 URL 추가
            }
            # 누락된 필수값 체크 (Pydantic 모델 생성 전)
            required_fields_from_form = {
                "title": self.title, "work_address": self.work_address, "work_place_name": self.work_place_name,
                "career": self.career, "employment_type": self.employment_type,
                "work_days": self.work_days, "description": self.description
            }
            for name, value in required_fields_from_form.items():
                 if value is None: # Form에서 ... 이 아닌 None으로 들어올 경우 체크
                      raise ValueError(f"필수 필드 '{name}'가 누락되었습니다.")


            # JobPostingCreate 모델 생성 시 Pydantic 유효성 검사 실행
            # (타입 변환 + 필수 필드 존재 여부 + validator 실행)
            job_posting_create_instance = JobPostingCreate(**create_data)

            return job_posting_create_instance

        except (ValueError, TypeError) as e: # PydanticValidationError 포함
            # 변환 중 발생한 에러를 HTTP 예외로 변환하여 반환
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"입력 값 오류: {e}"
            )
        except Exception as e: # 예상치 못한 에러 처리
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail=f"처리 중 오류 발생: {e}"
             )


# JobPostingCreateWithImage 클래스는 Form 데이터 처리 로직이 복잡해져서
# JobPostingCreateFormData 와 parse_to_job_posting_create 메서드로 대체함.
# class JobPostingCreateWithImage(BaseModel): ...


class JobPostingHelpers(BaseModel):
    """프론트엔드 등에서 Enum 옵션을 쉽게 사용하기 위한 헬퍼"""
    @staticmethod
    def get_education_options():
        """학력 옵션 목록 반환 (value: Enum 멤버 이름(key), label: Enum 값)"""
        return [{"value": edu.name, "label": edu.value} for edu in EducationEnum]

    @staticmethod
    def get_payment_method_options():
        """급여 지급 방식 옵션 목록 반환"""
        return [{"value": method.name, "label": method.value} for method in PaymentMethodEnum]

    @staticmethod
    def get_job_category_options():
        """직종 카테고리 옵션 목록 반환"""
        return [{"value": cat.name, "label": cat.value} for cat in JobCategoryEnum]

    @staticmethod
    def get_work_duration_options():
        """근무 기간 옵션 목록 반환"""
        return [{"value": dur.name, "label": dur.value} for dur in WorkDurationEnum]
