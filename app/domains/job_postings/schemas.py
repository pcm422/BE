import enum
from datetime import date, datetime
from typing import Type, TypeVar, Optional
import traceback

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, model_validator, Field, ValidationError
from fastapi import Form, HTTPException, status

from app.core.datetime_utils import to_kst
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
        # Removed past date validation for flexibility
        # if start_date and start_date < today:
        #     raise ValueError("모집 시작일은 현재 날짜 이후여야 합니다")

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
        # 대소문자 구분 없이 키로 찾기 시도
        return enum_class[value.lower()]
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

def _parse_bool(bool_str: str | bool | None, field_name: str) -> bool | None:
    """문자열이나 bool 값을 bool 객체로 변환"""
    if bool_str is None:
        return None
    if isinstance(bool_str, bool):
        return bool_str
    if isinstance(bool_str, str):
        if bool_str.lower() in ('true', '1', 'yes', 'y'):
            return True
        if bool_str.lower() in ('false', '0', 'no', 'n'):
            return False
    raise ValueError(f"{field_name}은(는) 불리언(True/False) 값이어야 합니다")


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

    # ORM 모델 -> Pydantic 모델 자동 변환 활성화
    model_config = ConfigDict(from_attributes=True)

    @field_validator('work_start_time', 'work_end_time')
    @classmethod
    def validate_time_format(cls, v: str | None) -> str | None:
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
    # 공고 '생성' 시 필요한 필드 정의
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
        """모델 레벨 유효성 검사 (주로 필드 간의 관계 검증)"""
        try:
            # 공통 날짜 검증 로직 호출
            _validate_recruitment_dates(
                self.recruit_period_start,
                self.recruit_period_end,
                self.is_always_recruiting
            )
            # 근무 시간 검증 (시작 시간이 종료 시간보다 빠르거나 같아야 함)
            if self.work_start_time and self.work_end_time:
                start_h, start_m = map(int, self.work_start_time.split(':'))
                end_h, end_m = map(int, self.work_end_time.split(':'))
                if start_h > end_h or (start_h == end_h and start_m > end_m):
                    raise ValueError("근무 시작 시간은 종료 시간보다 빨라야 합니다.")
        except ValueError as e:
            # 날짜 로직 등에서 ValueError 발생 시 Pydantic이 처리하도록 그대로 전달
            raise e
        return self

    @field_validator('salary', 'recruit_number')
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        """급여, 모집 인원 필드 유효성 검증 (0 이상)"""
        if v < 0:
            # 필드 이름을 동적으로 가져오기 (Pydantic v2 스타일 아님, 임시 방편)
            # field_name = cls.__fields__[inspect.currentframe().f_code.co_name.split('_')[-1]].alias
            field_name = "값" # 간단하게 처리
            if 'salary' in cls.model_fields: field_name = "급여"
            if 'recruit_number' in cls.model_fields: field_name = "모집 인원"
            raise ValueError(f"{field_name}은(는) 0 이상이어야 합니다")
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

    @field_serializer('created_at', 'updated_at', when_used='json')
    def serialize_datetime(self, value: datetime):
        return to_kst(value)



class JobPostingUpdate(JobPostingBase):
    # 공고 '수정' 시 사용할 스키마 (Base 상속, 모든 필드 선택적)
    # 모든 필드가 Optional이므로 추가 검증 필요 없음 (Base에서 처리)
    # work_days, description 등도 Base에서 Optional로 처리됨
    # work_duration의 Enum 타입도 Base에서 처리됨

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
            # 근무 시간 검증 (둘 다 None이 아닐 때)
            if self.work_start_time is not None and self.work_end_time is not None:
                start_h, start_m = map(int, self.work_start_time.split(':'))
                end_h, end_m = map(int, self.work_end_time.split(':'))
                if start_h > end_h or (start_h == end_h and start_m > end_m):
                    raise ValueError("근무 시작 시간은 종료 시간보다 빨라야 합니다.")
        except ValueError as e:
            raise e # ValueError 발생 시 그대로 전달
        return self

    @field_validator('salary', 'recruit_number')
    @classmethod
    def validate_non_negative_optional(cls, v: int | None) -> int | None:
        """수정 시 급여, 모집 인원 필드 유효성 검증 (선택적, None 가능)"""
        # 값이 None이 아니면서 0보다 작을 경우 에러
        if v is not None and v < 0:
            field_name = "값"
            if 'salary' in cls.model_fields: field_name = "급여"
            if 'recruit_number' in cls.model_fields: field_name = "모집 인원"
            raise ValueError(f"{field_name}은(는) 0 이상이어야 합니다")
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
        is_always_recruiting_str: str = Form("False", description="상시 모집 여부 ('True' 또는 'False')"),
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
        is_work_duration_negotiable_str: str = Form("False", description="근무 기간 협의 가능 여부 ('True' 또는 'False')"),
        career: Optional[str] = Form(None, description="경력 요구사항"),
        employment_type: Optional[str] = Form(None, description="고용 형태"),
        salary: Optional[str] = Form(None, description="급여 (숫자)"),
        work_days: Optional[str] = Form(None, description="근무 요일/스케줄"),
        is_work_days_negotiable_str: str = Form("False", description="근무 요일 협의 가능 여부 ('True' 또는 'False')"),
        is_schedule_based_str: str = Form("False", description="일정에 따른 근무 여부 ('True' 또는 'False')"),
        work_start_time: Optional[str] = Form(None, description="근무 시작 시간 (HH:MM)"),
        work_end_time: Optional[str] = Form(None, description="근무 종료 시간 (HH:MM)"),
        is_work_time_negotiable_str: str = Form("False", description="근무 시간 협의 가능 여부 ('True' 또는 'False')"),
        description: Optional[str] = Form(None, description="상세 설명"),
        summary: Optional[str] = Form(None, description="채용 공고 요약글"),
        latitude: Optional[str] = Form(None, description="근무지 위도 (숫자)"),
        longitude: Optional[str] = Form(None, description="근무지 경도 (숫자)"),
    ):
        # 주입받은 Form 데이터들을 인스턴스 변수에 저장
        self.title = title
        self.recruit_period_start = recruit_period_start
        self.recruit_period_end = recruit_period_end
        self.is_always_recruiting_str = is_always_recruiting_str
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
        self.is_work_duration_negotiable_str = is_work_duration_negotiable_str
        self.career = career
        self.employment_type = employment_type
        self.salary = salary
        self.work_days = work_days
        self.is_work_days_negotiable_str = is_work_days_negotiable_str
        self.is_schedule_based_str = is_schedule_based_str
        self.work_start_time = work_start_time
        self.work_end_time = work_end_time
        self.is_work_time_negotiable_str = is_work_time_negotiable_str
        self.description = description
        self.summary = summary
        self.latitude = latitude
        self.longitude = longitude

        # Boolean 값 파싱 추가 (Form에서 bool 직접 받기 어려움)
        try:
             self.is_always_recruiting = _parse_bool(is_always_recruiting_str, "상시 모집 여부")
             self.is_work_duration_negotiable = _parse_bool(is_work_duration_negotiable_str, "근무 기간 협의 가능 여부")
             self.is_work_days_negotiable = _parse_bool(is_work_days_negotiable_str, "근무 요일 협의 가능 여부")
             self.is_schedule_based = _parse_bool(is_schedule_based_str, "일정에 따른 근무 여부")
             self.is_work_time_negotiable = _parse_bool(is_work_time_negotiable_str, "근무 시간 협의 가능 여부")
        except ValueError as e:
             raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


    def parse_to_job_posting_create(self, postings_image_url: str | None) -> 'JobPostingCreate':
        """Form 데이터를 JobPostingCreate Pydantic 모델로 변환하고 유효성 검사 수행"""
        error_details = []
        parsed_data = {}
        try:
            parsed_data = {
                "title": self.title,
                "recruit_period_start": _parse_date(self.recruit_period_start, "모집 시작일"),
                "recruit_period_end": _parse_date(self.recruit_period_end, "모집 종료일"),
                "is_always_recruiting": self.is_always_recruiting,
                "education": _parse_enum(EducationEnum, self.education, "요구 학력"),
                "recruit_number": _parse_int(self.recruit_number, "모집 인원", min_value=0),
                "benefits": self.benefits,
                "preferred_conditions": self.preferred_conditions,
                "other_conditions": self.other_conditions,
                "work_address": self.work_address,
                "work_place_name": self.work_place_name,
                "payment_method": _parse_enum(PaymentMethodEnum, self.payment_method, "급여 지급 방식"),
                "job_category": _parse_enum(JobCategoryEnum, self.job_category, "직종 카테고리"),
                "work_duration": _parse_enum(WorkDurationEnum, self.work_duration, "근무 기간"),
                "is_work_duration_negotiable": self.is_work_duration_negotiable,
                "career": self.career,
                "employment_type": self.employment_type,
                "salary": _parse_int(self.salary, "급여", min_value=0),
                "work_days": self.work_days,
                "is_work_days_negotiable": self.is_work_days_negotiable,
                "is_schedule_based": self.is_schedule_based,
                "work_start_time": self.work_start_time,
                "work_end_time": self.work_end_time,
                "is_work_time_negotiable": self.is_work_time_negotiable,
                "description": self.description,
                "summary": self.summary,
                "postings_image": postings_image_url,
                "latitude": _parse_float(self.latitude, "위도"),
                "longitude": _parse_float(self.longitude, "경도"),
            }

            # 필수 필드가 None이 아닌지 다시 확인 (parse 함수에서 None 반환 가능성)
            required_fields = {
                "title": "채용공고 제목", "education": "요구 학력", "recruit_number": "모집 인원",
                "work_address": "근무지 주소", "work_place_name": "근무지명",
                "payment_method": "급여 지급 방식", "job_category": "직종 카테고리",
                "career": "경력 요구사항", "employment_type": "고용 형태",
                "salary": "급여",
            }
            for field, name in required_fields.items():
                if parsed_data.get(field) is None:
                     # 0은 유효한 값이므로 제외 (recruit_number, salary)
                     if field in ["recruit_number", "salary"] and parsed_data.get(field) == 0:
                         continue
                     error_details.append({"loc": [field], "msg": f"{name} 필드는 필수입니다."})

            # Pydantic 모델 생성 및 유효성 검사
            job_posting_create = JobPostingCreate(**parsed_data)
            return job_posting_create

        except ValueError as e:
            # 개별 필드 파싱/검증 오류 처리
            # 에러 메시지에서 필드명 추출 시도 (간단한 방식)
            field_name = "unknown"
            if "형식이 올바르지 않습니다" in str(e):
                field_name = str(e).split(" ")[0]
            elif "값:" in str(e):
                 field_name = str(e).split(" ")[2].replace(":", "") # "유효하지 않은 {field_name} 값:"
            elif "은(는)" in str(e):
                 field_name = str(e).split("은(는)")[0]

            # Pydantic 스타일 오류 상세 정보 구성
            error_details.append({"loc": [field_name], "msg": str(e)})
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_details,
            )
        except ValidationError as e:
             # Pydantic 모델 유효성 검사 실패 시 (예: model_validator)
             # Pydantic 오류 그대로 전달
             raise HTTPException(
                 status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                 detail=e.errors(),
             )
        except Exception as e:
            # 기타 예외 처리
            traceback.print_exc() # 디버깅용 트레이스백 출력
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"공고 데이터 처리 중 오류 발생: {e}"
            )


class JobPostingHelpers(BaseModel):
    # 정적 메소드를 통해 Enum 옵션 목록 제공 (프론트엔드 등에서 사용)

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