import enum
from datetime import date, datetime
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field
from fastapi import Form, HTTPException, status
from typing import Optional

from app.models.job_postings import (EducationEnum, JobCategoryEnum,
                                     PaymentMethodEnum, WorkDurationEnum)

# Enum 타입 힌팅을 위한 TypeVar
TEnum = TypeVar("TEnum", bound=enum.Enum)

# --- Helper Functions ---

def _validate_dates_logic(start_date: date | None, end_date: date | None, deadline: date | None, is_always_recruiting: bool | None) -> None:
    """공통 날짜 유효성 검사 로직"""
    # 상시 모집이 아닐 경우에만 날짜 검증
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
        return None # 빈 값이면 None 반환
    try:
        # ISO 형식(YYYY-MM-DD) 문자열을 date 객체로 변환
        return date.fromisoformat(date_str)
    except ValueError:
        # 형식 오류 시 에러 발생
        raise ValueError(f"{field_name} 형식이 올바르지 않습니다 (YYYY-MM-DD)")

def _parse_int(int_str: str | None, field_name: str, min_value: int | None = None) -> int | None:
    """문자열을 정수 객체로 변환하고 최소값 검증"""
    if int_str is None:
        return None # 빈 값이면 None 반환
    try:
        value = int(int_str) # 정수로 변환
        # 최소값 제약조건 확인
        if min_value is not None and value < min_value:
            raise ValueError(f"{field_name}은(는) {min_value} 이상이어야 합니다")
        return value
    except ValueError as e:
        # 최소값 검증에서 발생한 ValueError는 그대로 전달
        if min_value is not None and str(min_value) in str(e):
                raise e
        # 그 외 숫자 변환 실패 시 에러 발생
        raise ValueError(f"{field_name}은(는) 숫자여야 합니다")


def _parse_enum(enum_class: Type[TEnum], value: str | None, field_name: str) -> TEnum | None:
    """문자열을 Enum 객체로 변환 (key 또는 value로 검색)"""
    if value is None:
        return None # 빈 값이면 None 반환
    try:
        # Enum 키(멤버 이름)로 찾기 시도 (예: EducationEnum['대졸'])
        return enum_class[value]
    except KeyError:
        # Enum 값으로 찾기 시도 (예: member.value == '대졸')
        for member in enum_class:
            if member.value == value:
                return member
        # 이름과 값 모두로 찾기 실패 시 에러 발생
        valid_options = ", ".join([m.name for m in enum_class]) + " 또는 " + ", ".join([m.value for m in enum_class])
        raise ValueError(f"유효하지 않은 {field_name} 값: {value}. 가능한 값: {valid_options}")


# --- Pydantic Schemas ---

class JobPostingBase(BaseModel):
    # 모든 공고 스키마의 기본 클래스, 모든 필드는 선택적(Optional)
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

    # ORM 모델 -> Pydantic 모델 자동 변환 활성화
    model_config = ConfigDict(from_attributes=True)


class JobPostingCreate(JobPostingBase):
    # 공고 '생성' 시 필요한 필드 정의 (대부분 필수, ...은 필수 필드 의미)
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
    postings_image: str | None = Field(None, description="공고 이미지 URL (선택)") # 이미지는 생성 시 필수가 아님

    @model_validator(mode='after')
    def validate_model(self) -> 'JobPostingCreate':
        """모델 레벨 유효성 검사 (주로 필드 간의 관계 검증)"""
        try:
            # 공통 날짜 검증 로직 호출
            _validate_dates_logic(
                self.recruit_period_start,
                self.recruit_period_end,
                self.deadline_at,
                self.is_always_recruiting
            )
        except ValueError as e:
            # 날짜 로직 등에서 ValueError 발생 시 Pydantic이 처리하도록 그대로 전달
            raise e
        return self

    @field_validator('salary')
    @classmethod
    def validate_salary(cls, v: int) -> int:
        """특정 필드(급여) 유효성 검증 (0 이상)"""
        if v < 0:
            raise ValueError("급여는 0 이상이어야 합니다")
        return v


class JobPostingResponse(JobPostingBase):
    # API '응답'용 스키마 (DB에서 자동 생성된 필드 추가)
    id: int
    author_id: int
    company_id: int
    created_at: datetime
    updated_at: datetime
    # model_config (from_attributes=True) 는 Base에서 상속받음


class JobPostingUpdate(JobPostingBase):
    # 공고 '수정' 시 사용할 스키마 (Base 상속, 모든 필드 선택적)
    # 필요시 특정 필드만 업데이트 가능

    @model_validator(mode='after')
    def validate_model(self) -> 'JobPostingUpdate':
        """수정 시 모델 레벨 유효성 검사 (Optional 필드 고려)"""
        # 필드가 None일 수 있으므로, 값이 있는 필드 간의 관계만 검증
        try:
            _validate_dates_logic(
                self.recruit_period_start,
                self.recruit_period_end,
                self.deadline_at,
                self.is_always_recruiting
            )
        except ValueError as e:
            raise e # ValueError 발생 시 그대로 전달
        return self

    @field_validator('salary')
    @classmethod
    def validate_salary(cls, v: int | None) -> int | None:
        """수정 시 급여 필드 유효성 검증 (선택적, None 가능)"""
        # 값이 None이 아니면서 0보다 작을 경우 에러
        if v is not None and v < 0:
            raise ValueError("급여는 0 이상이어야 합니다")
        return v


class PaginatedJobPostingResponse(BaseModel):
    # 페이지네이션된 목록 응답 형식 정의
    items: list[JobPostingResponse] # 실제 데이터 목록
    total: int                      # 전체 아이템 개수
    skip: int                       # 건너뛴 아이템 개수
    limit: int                      # 페이지당 아이템 개수


class JobPostingCreateFormData:
    """
    Form 데이터 처리를 위한 의존성 주입용 클래스 (Pydantic 모델 아님!).
    FastAPI의 Depends() 와 함께 사용하여 Form 필드를 생성자 파라미터로 직접 받는다.
    """
    def __init__(
        self,
        # 각 필드는 Form(...)을 사용하여 FastAPI가 Form 데이터에서 값을 찾아 주입하도록 함
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
        # 주입받은 Form 데이터들을 인스턴스 변수에 저장
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
        """Form 데이터를 JobPostingCreate Pydantic 모델로 변환하고 유효성 검사 수행"""
        try:
            # 1. 헬퍼 함수들을 사용하여 문자열 데이터를 적절한 타입으로 변환
            start_date = _parse_date(self.recruit_period_start, "모집 시작일")
            end_date = _parse_date(self.recruit_period_end, "모집 종료일")
            deadline = _parse_date(self.deadline_at, "마감일")

            recruit_number_int = _parse_int(self.recruit_number, "모집 인원")
            salary_int = _parse_int(self.salary, "급여", min_value=0)

            education_enum = _parse_enum(EducationEnum, self.education, "학력")
            payment_method_enum = _parse_enum(PaymentMethodEnum, self.payment_method, "지불 방식")
            job_category_enum = _parse_enum(JobCategoryEnum, self.job_category, "직종 카테고리")
            work_duration_enum = _parse_enum(WorkDurationEnum, self.work_duration, "근무 기간")

            # 2. Pydantic 모델(JobPostingCreate) 생성을 위한 데이터 딕셔너리 준비
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
                "postings_image": postings_image_url # 서비스 계층에서 전달받은 이미지 URL
            }

            # 3. (선택적/방어적) Form(...)으로 받은 필수 필드가 None인지 추가 확인
            required_fields_from_form = {
                "title": self.title, "work_address": self.work_address, "work_place_name": self.work_place_name,
                "career": self.career, "employment_type": self.employment_type,
                "work_days": self.work_days, "description": self.description
                # 날짜, 숫자, Enum 등은 _parse 함수 또는 JobPostingCreate에서 필수 처리됨
            }
            for name, value in required_fields_from_form.items():
                # Form(...)으로 지정해도 간혹 None이 들어오는 경우를 대비한 방어 코드
                if value is None:
                    raise ValueError(f"필수 필드 '{name}'가 누락되었습니다.")

            # 4. JobPostingCreate 모델 인스턴스 생성 -> 이 과정에서 Pydantic 유효성 검사 실행됨
            # (타입 검증, 필수 필드 존재 여부, @field_validator, @model_validator 실행)
            job_posting_create_instance = JobPostingCreate(**create_data)

            # 5. 성공적으로 생성된 Pydantic 모델 인스턴스 반환
            return job_posting_create_instance

        except (ValueError, TypeError) as e: # 타입 변환 실패(ValueError), Pydantic 검증 실패(ValidationError는 ValueError 상속 안함 -> 수정 필요) 등
            # PydanticValidationError는 별도 처리하거나 Exception으로 잡아야 함
            # 여기서는 일단 ValueError, TypeError만 처리 (개선 가능)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"입력 값 오류: {e}"
            )
        except Exception as e: # 기타 예상치 못한 에러 처리
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"처리 중 오류 발생: {e}"
                )


class JobPostingHelpers(BaseModel):
    """프론트엔드 등에서 Enum 옵션을 쉽게 사용하기 위한 헬퍼 클래스"""
    @staticmethod
    def get_education_options():
        """학력 옵션 목록 반환 (value: Enum 멤버 이름(key), label: Enum 값(실제 표시될 값))"""
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