from datetime import date
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, constr, field_validator


### 기업 회원 공통 베이스
class CompanyUserBase(BaseModel):
    email: EmailStr  # 로그인 이메일
    manager_name: constr(min_length=1)  # 담당자 이름
    manager_phone: constr(min_length=8, max_length=15)  # 담당자 전화 번호
    manager_email: EmailStr  # 담당자 이메일
    company_name: constr(min_length=1)  # 기업명
    ceo_name: constr(min_length=1)  # 대표자 성함
    opening_date: str # 개업일자
    business_reg_number: str
    company_intro: constr(min_length=10)  # 기업 소개

    @field_validator("manager_phone")
    @classmethod
    def validate_phone_format(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError("담당자 전화번호는 숫자만 포함해야 합니다.")
        return v

    @field_validator("opening_date")
    @classmethod
    def validate_opening_date(cls, v):
        # YYYYMMDD 형태로 숫자만 허용
        if not v.isdigit():
            raise ValueError("개업일자(opening_date)는 숫자만 입력해야 합니다.")
        if len(v) != 8:
            raise ValueError("개업일자(opening_date)는 YYYYMMDD 형식이어야 합니다.")
        return v

    @field_validator("business_reg_number")
    @classmethod
    def validate_business_reg_number(cls, v):
        # 숫자만 10자리로 정확히 맞춰서 검사
        if not v.isdigit():
            raise ValueError("사업자등록번호는 숫자만 포함해야 합니다.")
        if len(v) != 10:
            raise ValueError("사업자등록번호는 정확히 10자리여야 합니다.")
        return v

### 패스워드 확인용 믹스인
class PasswordMixin(BaseModel):
    password: constr(min_length=8)
    confirm_password: constr(min_length=8)


### 기업 회원 가입 요청
class CompanyUserRegisterRequest(CompanyUserBase, PasswordMixin):
    pass


### 기업 회원 로그인 요청
class CompanyUserLoginRequest(BaseModel):
    email: EmailStr
    password: str


### 리프레쉬 토큰 요청
class CompanyTokenRefreshRequest(BaseModel):
    refresh_token: str


### 기업 회원 수정 요청 (선택필드)
class CompanyUserUpdateRequest(BaseModel):
    manager_name: Optional[constr(min_length=1)] = None
    manager_phone: Optional[constr(min_length=8, max_length=15)] = None
    manager_email: Optional[EmailStr] = None
    password: Optional[constr(min_length=8)] = None
    confirm_password: Optional[constr(min_length=8)] = None
    company_intro: Optional[str] = None
    address: Optional[str] = None
    company_image: Optional[str] = None


### 아이디 찾기 요청
class FindCompanyUserEmail(BaseModel):
    business_reg_number: str
    opening_date: str
    ceo_name: str


### 비밀번호 재설정 요청
class ResetCompanyUserPassword(FindCompanyUserEmail):
    email: EmailStr
    new_password: constr(min_length=8)
    confirm_password: constr(min_length=8)


### 성공 응답 스키마(Generic)
T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    status: str = "success"
    message: str
    data: Optional[T] = None


class JobPostingsSummary(BaseModel):  # 공고 요약
    id: int
    title: str
    summary: Optional[str]
    work_address: str
    is_always_recruiting: bool
    recruit_period_start: date
    recruit_period_end: date
    model_config = ConfigDict(from_attributes=True)


class CompanyUserRegisterResponse(BaseModel):
    company_user_id: int
    email: EmailStr
    company_name: str

    model_config = ConfigDict(from_attributes=True)


class CompanyUserLoginResponse(BaseModel):  # 로그인 응답
    company_user_id: int
    email: EmailStr
    company_name: str
    access_token: str
    refresh_token: str

    model_config = ConfigDict(from_attributes=True)


class CompanyUserUpdateResponse(BaseModel):
    company_user_id: int
    email: EmailStr
    company_name: str
    # 수정된 값 필드
    manager_name: str
    manager_email: EmailStr
    manager_phone: str
    company_intro: str
    address: Optional[str]
    company_image: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class CompanyUserInfo(BaseModel):
    company_user_id: int
    email: EmailStr
    company_id: int
    company_name: str
    manager_name: str
    manager_email: EmailStr
    manager_phone: str
    business_reg_number: str
    opening_date: str
    ceo_name: str
    company_intro: str
    address: Optional[str] = None
    company_image: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
    job_postings: List[JobPostingsSummary] = Field(default_factory=list)
