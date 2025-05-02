import enum
from datetime import date, datetime
from typing import Type, TypeVar, Optional

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, model_validator, Field
from fastapi import Form

from app.core.datetime_utils import to_kst # 시간대 변환 유틸리티
from app.models.job_postings import (EducationEnum, JobCategoryEnum,
                                     PaymentMethodEnum, WorkDurationEnum)

# Enum 타입 힌팅용
TEnum = TypeVar("TEnum", bound=enum.Enum)

# 정렬 옵션 Enum
class SortOptions(str, enum.Enum):
    LATEST = "latest"
    SALARY_HIGH = "salary_high"
    SALARY_LOW = "salary_low"

# --- 스키마 내부/라우터용 파싱 헬퍼 함수 --- 

def _validate_recruitment_dates(start_date: date | None, end_date: date | None, is_always_recruiting: bool | None) -> None:
    """모집 시작일/종료일 유효성 검사 (Pydantic 모델 검증용)"""
    if not is_always_recruiting:
        if start_date and end_date and start_date > end_date:
            raise ValueError("모집 시작일은 종료일보다 빨라야 합니다")

def _parse_date(date_str: str | None, field_name: str) -> date | None:
    """날짜 문자열(YYYY-MM-DD)을 date 객체로 파싱"""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(f"{field_name} 형식이 올바르지 않습니다 (YYYY-MM-DD)")

def _parse_int(int_str: str | None, field_name: str, min_value: int | None = None) -> int | None:
    """문자열을 정수로 파싱 (최소값 검증 포함)"""
    if int_str is None:
        return None
    try:
        value = int(int_str)
        if min_value is not None and value < min_value:
            raise ValueError(f"{field_name}은(는) {min_value} 이상이어야 합니다")
        return value
    except (ValueError, TypeError):
        # 숫자 아닌 값 or 최소값 미만 시 에러 메시지 포함하여 raise
        if min_value is not None and isinstance(int_str, str) and int_str.isdigit() and int(int_str) < min_value:
             raise ValueError(f"{field_name}은(는) {min_value} 이상이어야 합니다")
        raise ValueError(f"{field_name}은(는) 숫자(정수)여야 합니다")

def _parse_enum(enum_class: Type[TEnum], value: str | None, field_name: str) -> TEnum | None:
    """문자열을 Enum 멤버로 파싱 (Enum 키 또는 값으로 검색)"""
    if value is None:
        return None
    try:
        sanitized_value = value.strip().lower()
        # 키(이름)로 찾기 (대소문자 무시)
        return enum_class[sanitized_value]
    except KeyError:
        # 값으로 찾기 (대소문자 무시)
        for member in enum_class:
            # member.value가 문자열이라고 가정
            if isinstance(member.value, str) and member.value.lower() == sanitized_value:
                return member
        valid_options = ", ".join([m.name for m in enum_class]) + " 또는 " + ", ".join([m.value for m in enum_class if isinstance(m.value, str)])
        raise ValueError(f"유효하지 않은 {field_name} 값: {value}. 가능한 값: {valid_options}")

def _parse_float(float_str: str | None, field_name: str) -> float | None:
    """문자열을 실수로 파싱"""
    if float_str is None:
        return None
    try:
        return float(float_str)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name}은(는) 숫자(실수)여야 합니다")

def _parse_bool(bool_str: str | bool | None, field_name: str) -> bool | None:
    """문자열 또는 bool 값을 bool 객체로 파싱"""
    if bool_str is None:
        return None
    if isinstance(bool_str, bool):
        return bool_str
    if isinstance(bool_str, str):
        lowered_str = bool_str.lower().strip()
        if lowered_str in ('true', '1', 'yes', 'y'):
            return True
        if lowered_str in ('false', '0', 'no', 'n'):
            return False
    raise ValueError(f"{field_name}은(는) 불리언(True/False) 값이어야 합니다")


# --- Pydantic 스키마 정의 --- (데이터 유효성 검사 및 구조 정의)

class JobPostingBase(BaseModel):
    """채용 공고 데이터의 기본 필드 정의 (모든 필드 선택적)"""
    title: Optional[str] = Field(None, description="채용공고 제목")
    recruit_period_start: Optional[date] = Field(None, description="모집 시작일")
    recruit_period_end: Optional[date] = Field(None, description="모집 종료일")
    is_always_recruiting: Optional[bool] = Field(False, description="상시 모집 여부")
    education: Optional[EducationEnum] = Field(None, description="요구 학력")
    recruit_number: Optional[int] = Field(None, description="모집 인원 (0은 '인원 미정')")
    benefits: Optional[str] = Field(None, description="복리 후생")
    preferred_conditions: Optional[str] = Field(None, description="우대 조건")
    other_conditions: Optional[str] = Field(None, description="기타 조건")
    work_address: Optional[str] = Field(None, description="근무지 주소")
    work_place_name: Optional[str] = Field(None, description="근무지명")
    region1: Optional[str] = Field(None, max_length=50, description="지역(시/도)")
    region2: Optional[str] = Field(None, max_length=50, description="지역(구/군)")
    payment_method: Optional[PaymentMethodEnum] = Field(None, description="급여 지급 방식")
    job_category: Optional[JobCategoryEnum] = Field(None, description="직종 카테고리")
    work_duration: Optional[WorkDurationEnum] = Field(None, description="근무 기간")
    is_work_duration_negotiable: Optional[bool] = Field(False, description="근무 기간 협의 가능 여부")
    career: Optional[str] = Field(None, description="경력 요구사항")
    employment_type: Optional[str] = Field(None, description="고용 형태")
    salary: Optional[int] = Field(None, description="급여")
    work_days: Optional[str] = Field(None, description="근무 요일/스케줄")
    is_work_days_negotiable: Optional[bool] = Field(False, description="근무 요일 협의 가능 여부")
    is_schedule_based: Optional[bool] = Field(False, description="일정에 따른 근무 여부")
    work_start_time: Optional[str] = Field(None, max_length=5, description="근무 시작 시간 (HH:MM)")
    work_end_time: Optional[str] = Field(None, max_length=5, description="근무 종료 시간 (HH:MM)")
    is_work_time_negotiable: Optional[bool] = Field(False, description="근무 시간 협의 가능 여부")
    description: Optional[str] = Field(None, description="상세 설명")
    summary: Optional[str] = Field(None, description="채용 공고 요약글")
    postings_image: Optional[str] = Field(None, description="공고 이미지 URL")
    latitude: Optional[float] = Field(None, description="근무지 위도")
    longitude: Optional[float] = Field(None, description="근무지 경도")

    model_config = ConfigDict(from_attributes=True) # ORM 객체와 호환

    @field_validator('work_start_time', 'work_end_time')
    @classmethod
    def validate_time_format(cls, v: str | None) -> str | None:
        """근무 시간 HH:MM 형식 검증"""
        if v is None:
            return v
        if not isinstance(v, str) or len(v) != 5 or v[2] != ':':
             raise ValueError("시간 형식은 HH:MM 이어야 합니다.")
        try:
            hour, minute = map(int, v.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("유효하지 않은 시간 값입니다.")
        except ValueError:
            raise ValueError("시간 형식은 HH:MM 이어야 합니다.")
        return v


class JobPostingCreate(JobPostingBase):
    """채용 공고 생성 시 필요한 데이터 스키마 (필수 필드 정의)"""
    title: str = Field(..., description="채용공고 제목")
    recruit_period_start: Optional[date] = Field(None, description="모집 시작일")
    recruit_period_end: Optional[date] = Field(None, description="모집 종료일")
    is_always_recruiting: bool = Field(False, description="상시 모집 여부")
    education: EducationEnum = Field(..., description="요구 학력")
    recruit_number: int = Field(..., description="모집 인원 (0은 '인원 미정')")
    work_address: str = Field(..., description="근무지 주소")
    work_place_name: str = Field(..., description="근무지명")
    region1: Optional[str] = Field(None, max_length=50, description="지역(시/도) (선택)")
    region2: Optional[str] = Field(None, max_length=50, description="지역(구/군) (선택)")
    payment_method: PaymentMethodEnum = Field(..., description="급여 지급 방식")
    job_category: JobCategoryEnum = Field(..., description="직종 카테고리")
    work_duration: Optional[WorkDurationEnum] = Field(None, description="근무 기간")
    is_work_duration_negotiable: bool = Field(False, description="근무 기간 협의 가능 여부")
    career: str = Field(..., description="경력 요구사항")
    employment_type: str = Field(..., description="고용 형태")
    salary: int = Field(..., description="급여")
    work_days: Optional[str] = Field(None, description="근무 요일/스케줄")
    is_work_days_negotiable: bool = Field(False, description="근무 요일 협의 가능 여부")
    is_schedule_based: bool = Field(False, description="일정에 따른 근무 여부")
    work_start_time: Optional[str] = Field(None, max_length=5, description="근무 시작 시간 (HH:MM)")
    work_end_time: Optional[str] = Field(None, max_length=5, description="근무 종료 시간 (HH:MM)")
    is_work_time_negotiable: bool = Field(False, description="근무 시간 협의 가능 여부")
    description: Optional[str] = Field(None, description="상세 설명")
    postings_image: Optional[str] = Field(None, description="공고 이미지 URL (선택)")
    latitude: Optional[float] = Field(None, description="근무지 위도 (선택)")
    longitude: Optional[float] = Field(None, description="근무지 경도 (선택)")

    @model_validator(mode='after')
    def validate_model(self) -> 'JobPostingCreate':
        """모델 레벨 유효성 검사 (필드 간 관계 등)"""
        try:
            _validate_recruitment_dates(
                self.recruit_period_start,
                self.recruit_period_end,
                self.is_always_recruiting
            )
            if self.work_start_time and self.work_end_time:
                start_h, start_m = map(int, self.work_start_time.split(':'))
                end_h, end_m = map(int, self.work_end_time.split(':'))
                if start_h > end_h or (start_h == end_h and start_m > end_m):
                    raise ValueError("근무 시작 시간은 종료 시간보다 빨라야 합니다.")
        except ValueError as e:
            raise e # Pydantic이 처리하도록 ValueError 재발생
        return self

    @field_validator('salary', 'recruit_number')
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        """급여, 모집 인원은 0 이상이어야 함"""
        if v < 0:
            field_name = "값"
            if 'salary' in cls.model_fields: field_name = "급여"
            if 'recruit_number' in cls.model_fields: field_name = "모집 인원"
            raise ValueError(f"{field_name}은(는) 0 이상이어야 합니다")
        return v


class JobPostingResponse(JobPostingBase):
    """API 응답용 채용 공고 스키마 (DB 자동 생성 필드 포함)"""
    id: int
    author_id: int
    company_id: int
    created_at: datetime
    updated_at: datetime
    is_favorited: Optional[bool] = Field(None, description="현재 로그인한 사용자의 즐겨찾기 여부 (비로그인 시 null)")

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('created_at', 'updated_at', when_used='json')
    def serialize_datetime(self, value: datetime):
        """날짜/시간 필드를 KST로 변환하여 직렬화"""
        return to_kst(value)


class JobPostingUpdate(JobPostingBase):
    """채용 공고 수정 시 사용할 스키마 (모든 필드 선택적)"""
    # Base 상속, 추가 필드 없음

    @model_validator(mode='after')
    def validate_model(self) -> 'JobPostingUpdate':
        """수정 시 모델 레벨 유효성 검사 (Optional 필드 고려)"""
        try:
            _validate_recruitment_dates(
                self.recruit_period_start,
                self.recruit_period_end,
                self.is_always_recruiting
            )
            if self.work_start_time is not None and self.work_end_time is not None:
                start_h, start_m = map(int, self.work_start_time.split(':'))
                end_h, end_m = map(int, self.work_end_time.split(':'))
                if start_h > end_h or (start_h == end_h and start_m > end_m):
                    raise ValueError("근무 시작 시간은 종료 시간보다 빨라야 합니다.")
        except ValueError as e:
            raise e
        return self

    @field_validator('salary', 'recruit_number')
    @classmethod
    def validate_non_negative_optional(cls, v: int | None) -> int | None:
        """수정 시 급여, 모집 인원은 0 이상이어야 함 (None 허용)"""
        if v is not None and v < 0:
            field_name = "값"
            if 'salary' in cls.model_fields: field_name = "급여"
            if 'recruit_number' in cls.model_fields: field_name = "모집 인원"
            raise ValueError(f"{field_name}은(는) 0 이상이어야 합니다")
        return v


class PaginatedJobPostingResponse(BaseModel):
    """페이지네이션된 채용 공고 목록 응답 스키마"""
    items: list[JobPostingResponse]
    total: int
    skip: int
    limit: int


class JobPostingCreateFormData:
    """
    채용 공고 생성 시 Form 데이터 수신용 클래스 (Depends 의존성).
    파싱 및 검증은 라우터에서 수행.
    """
    def __init__(
        self,
        # Form 필드는 문자열로 수신 (타입 변환은 라우터에서)
        title: str = Form(..., description="채용공고 제목"),
        recruit_period_start: Optional[str] = Form(None, description="모집 시작일 (YYYY-MM-DD)"),
        recruit_period_end: Optional[str] = Form(None, description="모집 종료일 (YYYY-MM-DD)"),
        is_always_recruiting: str = Form("False", description="상시 모집 여부 ('True'/'False')"),
        education: Optional[str] = Form(None, description=f"요구 학력 (가능한 값: {', '.join([e.name for e in EducationEnum])} 또는 {', '.join([e.value for e in EducationEnum])})"),
        recruit_number: Optional[str] = Form(None, description="모집 인원 (숫자, 0은 '인원 미정')"),
        benefits: Optional[str] = Form(None, description="복리 후생"),
        preferred_conditions: Optional[str] = Form(None, description="우대 조건"),
        other_conditions: Optional[str] = Form(None, description="기타 조건"),
        work_address: Optional[str] = Form(None, description="근무지 주소"),
        work_place_name: Optional[str] = Form(None, description="근무지명"),
        region1: Optional[str] = Form(None, description="지역(시/도)"),
        region2: Optional[str] = Form(None, description="지역(구/군)"),
        payment_method: Optional[str] = Form(None, description=f"급여 지급 방식 (가능한 값: {', '.join([e.name for e in PaymentMethodEnum])} 또는 {', '.join([e.value for e in PaymentMethodEnum])})"),
        job_category: Optional[str] = Form(None, description=f"직종 카테고리 (가능한 값: {', '.join([e.name for e in JobCategoryEnum])} 또는 {', '.join([e.value for e in JobCategoryEnum])})"),
        work_duration: Optional[str] = Form(None, description=f"근무 기간 (가능한 값: {', '.join([e.name for e in WorkDurationEnum])} 또는 {', '.join([e.value for e in WorkDurationEnum])})"),
        is_work_duration_negotiable: str = Form("False", description="근무 기간 협의 가능 여부 ('True'/'False')"),
        career: Optional[str] = Form(None, description="경력 요구사항"),
        employment_type: Optional[str] = Form(None, description="고용 형태"),
        salary: Optional[str] = Form(None, description="급여 (숫자)"),
        work_days: Optional[str] = Form(None, description="근무 요일/스케줄"),
        is_work_days_negotiable: str = Form("False", description="근무 요일 협의 가능 여부 ('True'/'False')"),
        is_schedule_based: str = Form("False", description="일정에 따른 근무 여부 ('True'/'False')"),
        work_start_time: Optional[str] = Form(None, description="근무 시작 시간 (HH:MM)"),
        work_end_time: Optional[str] = Form(None, description="근무 종료 시간 (HH:MM)"),
        is_work_time_negotiable: str = Form("False", description="근무 시간 협의 가능 여부 ('True'/'False')"),
        description: Optional[str] = Form(None, description="상세 설명"),
        summary: Optional[str] = Form(None, description="채용 공고 요약글"),
        latitude: Optional[str] = Form(None, description="근무지 위도 (숫자)"),
        longitude: Optional[str] = Form(None, description="근무지 경도 (숫자)"),
    ):
        # Form 데이터를 인스턴스 변수에 저장
        self.title = title
        self.recruit_period_start = recruit_period_start
        self.recruit_period_end = recruit_period_end
        self.is_always_recruiting_str = is_always_recruiting # bool 파싱용
        self.education = education
        self.recruit_number = recruit_number
        self.benefits = benefits
        self.preferred_conditions = preferred_conditions
        self.other_conditions = other_conditions
        self.work_address = work_address
        self.work_place_name = work_place_name
        self.region1 = region1
        self.region2 = region2
        self.payment_method = payment_method
        self.job_category = job_category
        self.work_duration = work_duration
        self.is_work_duration_negotiable_str = is_work_duration_negotiable # bool 파싱용
        self.career = career
        self.employment_type = employment_type
        self.salary = salary
        self.work_days = work_days
        self.is_work_days_negotiable_str = is_work_days_negotiable # bool 파싱용
        self.is_schedule_based_str = is_schedule_based # bool 파싱용
        self.work_start_time = work_start_time
        self.work_end_time = work_end_time
        self.is_work_time_negotiable_str = is_work_time_negotiable # bool 파싱용
        self.description = description
        self.summary = summary
        self.latitude = latitude
        self.longitude = longitude


class JobPostingHelpers(BaseModel):
    """프론트엔드 등에서 사용할 Enum 선택 옵션 제공 헬퍼"""

    @staticmethod
    def get_education_options():
        return [{"value": e.name, "label": e.value} for e in EducationEnum]

    @staticmethod
    def get_payment_method_options():
        return [{"value": e.name, "label": e.value} for e in PaymentMethodEnum]

    @staticmethod
    def get_job_category_options():
        return [{"value": e.name, "label": e.value} for e in JobCategoryEnum]

    @staticmethod
    def get_work_duration_options():
        return [{"value": e.name, "label": e.value} for e in WorkDurationEnum]