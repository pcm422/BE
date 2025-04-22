import enum
from datetime import date, datetime
from typing import Type, TypeVar, Optional
import traceback

from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field, ValidationError
from fastapi import Form, HTTPException, status

from app.models.job_postings import (EducationEnum, JobCategoryEnum,
                                     PaymentMethodEnum, WorkDurationEnum)

# Enum 타입 힌팅을 위한 TypeVar
TEnum = TypeVar("TEnum", bound=enum.Enum)

# --- Helper Functions ---

def _validate_recruitment_dates(start_date: date | None, end_date: date | None, is_always_recruiting: bool | None) -> None:
    """공통 채용 기간 날짜 유효성 검사 로직"""
    # 상시 모집이 아닐 경우에만 날짜 검증
    if not is_always_recruiting:
        today = date.today()

        # 시작일과 종료일 관계 검증 (둘 다 존재할 때)
        if start_date and end_date and start_date > end_date:
            raise ValueError("모집 시작일은 종료일보다 빨라야 합니다")

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

def _parse_float(float_str: str | None, field_name: str) -> float | None:
    """문자열을 실수 객체로 변환"""
    if float_str is None:
        return None # 빈 값이면 None 반환
    try:
        # 문자열을 float으로 변환
        return float(float_str)
    except ValueError:
        # 변환 실패 시 에러 발생
        raise ValueError(f"{field_name}은(는) 숫자(실수)여야 합니다")


# --- Pydantic Schemas ---

class JobPostingBase(BaseModel):
    # 모든 공고 스키마의 기본 클래스, 모든 필드는 선택적(Optional)
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
    payment_method: Optional[PaymentMethodEnum] = Field(None, description="급여 지급 방식")
    job_category: Optional[JobCategoryEnum] = Field(None, description="직종 카테고리")
    work_duration: Optional[WorkDurationEnum] = Field(None, description="근무 기간")
    career: Optional[str] = Field(None, description="경력 요구사항")
    employment_type: Optional[str] = Field(None, description="고용 형태")
    salary: Optional[int] = Field(None, description="급여")
    work_days: Optional[str] = Field(None, description="근무 요일/스케줄")
    description: Optional[str] = Field(None, description="상세 설명")
    postings_image: Optional[str] = Field(None, description="공고 이미지 URL")
    latitude: Optional[float] = Field(None, description="근무지 위도")
    longitude: Optional[float] = Field(None, description="근무지 경도")

    # ORM 모델 -> Pydantic 모델 자동 변환 활성화
    model_config = ConfigDict(from_attributes=True)


class JobPostingCreate(JobPostingBase):
    # 공고 '생성' 시 필요한 필드 정의 (대부분 필수, ...은 필수 필드 의미)
    title: str = Field(..., description="채용공고 제목")
    recruit_period_start: Optional[date] = Field(None, description="모집 시작일")
    recruit_period_end: Optional[date] = Field(None, description="모집 종료일")
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
    work_days: str = Field(..., description="근무 요일/스케줄")
    description: str = Field(..., description="상세 설명")
    postings_image: Optional[str] = Field(None, description="공고 이미지 URL (선택)")
    latitude: Optional[float] = Field(None, description="근무지 위도 (선택)")
    longitude: Optional[float] = Field(None, description="근무지 경도 (선택)")

    @model_validator(mode='after')
    def validate_model(self) -> 'JobPostingCreate':
        """모델 레벨 유효성 검사 (주로 필드 간의 관계 검증)"""
        try:
            # 공통 날짜 검증 로직 호출
            _validate_recruitment_dates(
                self.recruit_period_start,
                self.recruit_period_end,
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
    is_favorited: Optional[bool] = Field(None, description="현재 로그인한 사용자의 즐겨찾기 여부 (비로그인 시 null)")

    model_config = ConfigDict(from_attributes=True)


class JobPostingUpdate(JobPostingBase):
    # 공고 '수정' 시 사용할 스키마 (Base 상속, 모든 필드 선택적)
    # 필요시 특정 필드만 업데이트 가능

    @model_validator(mode='after')
    def validate_model(self) -> 'JobPostingUpdate':
        """수정 시 모델 레벨 유효성 검사 (Optional 필드 고려)"""
        # 필드가 None일 수 있으므로, 값이 있는 필드 간의 관계만 검증
        try:
            _validate_recruitment_dates(
                self.recruit_period_start,
                self.recruit_period_end,
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
    items: list[JobPostingResponse] # 실제 데이터 목록 (List 타입 힌트 사용)
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
        work_days: Optional[str] = Form(None, description="근무 요일/스케줄"),
        description: Optional[str] = Form(None, description="상세 설명"),
        latitude: Optional[str] = Form(None, description="근무지 위도 (숫자)"),
        longitude: Optional[str] = Form(None, description="근무지 경도 (숫자)"),
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
        self.work_days = work_days
        self.description = description
        self.latitude = latitude
        self.longitude = longitude

    def parse_to_job_posting_create(self, postings_image_url: str | None) -> 'JobPostingCreate':
        """
        Form 데이터 필드를 파싱하고 JobPostingCreate Pydantic 모델로 변환 및 검증한다.
        파싱 오류 발생 시 우선적으로 HTTPException(422)을 발생시킨다.
        파싱 성공 후 Pydantic 모델 생성/검증 중 오류 발생 시 ValidationError를 잡아 HTTPException(422)으로 변환한다.
        """
        parsed_data = {}
        parsing_errors = {} # 개별 필드 파싱 오류 수집

        # --- 각 필드 파싱 시도 및 오류 수집 ---
        # Title (Required String)
        if not self.title:
            parsing_errors["title"] = "제목은 필수입니다."
        else:
            parsed_data["title"] = self.title

        # Dates (Optional Date)
        try:
            parsed_data["recruit_period_start"] = _parse_date(self.recruit_period_start, "모집 시작일")
        except ValueError as e:
            parsing_errors["recruit_period_start"] = str(e)
        try:
            parsed_data["recruit_period_end"] = _parse_date(self.recruit_period_end, "모집 종료일")
        except ValueError as e:
            parsing_errors["recruit_period_end"] = str(e)

        # Boolean (Handled by FastAPI/Pydantic)
        parsed_data["is_always_recruiting"] = self.is_always_recruiting

        # Required Enums
        required_enums = {
            "education": (EducationEnum, "학력"),
            "payment_method": (PaymentMethodEnum, "급여 지급 방식"),
            "job_category": (JobCategoryEnum, "직종 카테고리"),
            "work_duration": (WorkDurationEnum, "근무 기간"),
        }
        for field, (enum_cls, name) in required_enums.items():
            try:
                enum_val = _parse_enum(enum_cls, getattr(self, field), name)
                parsed_data[field] = enum_val
            except ValueError as e:
                parsing_errors[field] = str(e)

        # Required Integers (with validation)
        try:
            recruit_num_val = _parse_int(self.recruit_number, "모집 인원", min_value=0)
            if recruit_num_val is None:
                parsing_errors["recruit_number"] = "모집 인원은 필수입니다."
            parsed_data["recruit_number"] = recruit_num_val
        except ValueError as e:
            parsing_errors["recruit_number"] = str(e)

        try:
            salary_val = _parse_int(self.salary, "급여", min_value=0)
            if salary_val is None:
                parsing_errors["salary"] = "급여는 필수입니다."
            parsed_data["salary"] = salary_val
        except ValueError as e:
            parsing_errors["salary"] = str(e)

        # Required Strings
        required_strings = {
            "work_address": "근무지 주소", "work_place_name": "근무지명",
            "career": "경력 요구사항", "employment_type": "고용 형태",
            "work_days": "근무 요일/스케줄", "description": "상세 설명"
        }
        for field, name in required_strings.items():
            value = getattr(self, field)
            if not value:
                parsing_errors[field] = f"{name}은(는) 필수입니다."
            else:
                parsed_data[field] = value

        # Optional Floats
        try:
            parsed_data["latitude"] = _parse_float(self.latitude, "위도")
        except ValueError as e:
            parsing_errors["latitude"] = str(e)
        try:
            parsed_data["longitude"] = _parse_float(self.longitude, "경도")
        except ValueError as e:
            parsing_errors["longitude"] = str(e)

        # Optional Strings (이미 __init__에서 할당됨, parsed_data에 추가만)
        parsed_data["benefits"] = self.benefits
        parsed_data["preferred_conditions"] = self.preferred_conditions
        parsed_data["other_conditions"] = self.other_conditions

        # Image URL
        parsed_data["postings_image"] = postings_image_url

        # --- 파싱 오류 우선 처리 ---
        if parsing_errors:
            # Pydantic 오류 형식과 유사하게 detail 구성
            error_details = [{"loc": [field], "msg": msg, "type": "value_error"} for field, msg in parsing_errors.items()]
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_details)

        # --- 파싱 오류 없을 시 Pydantic 모델 생성 및 검증 시도 ---
        try:
            # parsed_data 딕셔너리를 사용하여 JobPostingCreate 인스턴스 생성
            # 이 과정에서 Pydantic의 모델 레벨 유효성 검사(@model_validator)가 추가로 실행됨
            job_posting_instance = JobPostingCreate(**parsed_data)
            return job_posting_instance
        except ValidationError as e:
            # Pydantic 유효성 검사 실패 시 (예: @model_validator의 날짜 로직)
            # Pydantic의 e.errors()는 FastAPI가 이해하는 형식이므로 그대로 전달
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
        except Exception as e:
            # 그 외 예상치 못한 오류 (Pydantic 생성 중 발생 가능)
            traceback.print_exc() # 서버 로그에 상세 오류 출력
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"데이터 검증 중 예상치 못한 오류 발생: {e}")


class JobPostingHelpers(BaseModel):
    """프론트엔드 등에서 Enum 옵션을 쉽게 사용하기 위한 헬퍼 클래스"""
    @staticmethod
    def get_education_options():
        """학력 옵션 목록 반환 (value: Enum 멤버 이름(key), label: Enum 값(실제 표시될 값))"""
        return [{"name": edu.name, "value": edu.value} for edu in EducationEnum]

    @staticmethod
    def get_payment_method_options():
        """급여 지급 방식 옵션 목록 반환"""
        return [{"name": method.name, "value": method.value} for method in PaymentMethodEnum]

    @staticmethod
    def get_job_category_options():
        """직종 카테고리 옵션 목록 반환"""
        return [{"name": cat.name, "value": cat.value} for cat in JobCategoryEnum]

    @staticmethod
    def get_work_duration_options():
        """근무 기간 옵션 목록 반환"""
        return [{"name": dur.name, "value": dur.value} for dur in WorkDurationEnum]