from datetime import date
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, EmailStr, Field
from pydantic.generics import GenericModel
from typing_extensions import List


### 기업 회원 공통 베이스
class CompanyUserBase(BaseModel):
    email: EmailStr  # 로그인 이메일
    manager_name: str  # 담당자 이름
    manager_phone: str  # 담당자 전화 번호
    manager_email: EmailStr  # 담당자 이메일
    company_name: str  # 기업명
    ceo_name: str  # 대표자 성함
    opening_date: date  # 개업 날짜 (YYYY-MM-DD)
    business_reg_number: str  # 사업자등록번호
    company_intro: str  # 기업 소개


### 패스워드 확인용 믹스인
class PasswordMixin(BaseModel):
    password: str
    confirm_password: str


### 기업 화원 가입 요청
class CompanyUserRegisterRequest(CompanyUserBase, PasswordMixin):
    pass


### 기업 회원 로그인 요청
class CompanyUserLoginRequest(BaseModel):
    email: EmailStr
    password: str


### 기업 회원 수정 요청 (선택필드)
class CompanyUserUpdateRequest(BaseModel):
    manager_name: Optional[str] = None
    manager_phone: Optional[str] = None
    manager_email: Optional[EmailStr] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None
    company_intro: Optional[str] = None
    address: Optional[str] = None
    company_image: Optional[str] = None


### 아이디 찾기 요청
class FindCompanyUserEmail(BaseModel):
    business_reg_number: str
    opening_date: date
    ceo_name: str


### 비밀번호 재설정 요청
class ResetCompanyUserPassword(FindCompanyUserEmail):
    email: EmailStr
    new_password: str
    confirm_password: str
