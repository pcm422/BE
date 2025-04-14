from datetime import date

from pydantic import BaseModel, EmailStr


# 기업 회원 가입 - 요청 바디용
class CompanyUserRequest(BaseModel):
    email: EmailStr  # 로그인 이메일
    password: str  # 비밀 번호

    # 기업 정보
    company_name: str  # 기업명
    ceo_name: str  # 대표자 성함
    opening_date: date  # 개업 날짜 (YYYY-MM-DD)
    business_reg_number: str  # 사업자등록번호
    company_intro: str  # 기업 소개

    # 담당자
    manager_name: str  # 담당자 이름
    manager_phone: str  # 담당자 전화 번호
    manager_email: EmailStr  # 담당자 이메일

# 사업자등록번호 유효성 확인
class BRNValidationRequest(BaseModel):
    business_reg_number: str
    opening_date: str   # YYYYMMDD
    ceo_name: str

# 기업 회원 로그인
class CompanyUserLoginRequest(BaseModel):
    email: EmailStr
    password: str

