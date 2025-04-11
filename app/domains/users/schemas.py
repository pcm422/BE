from datetime import datetime
from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional
from enum import Enum

# 관심분야 Enum (Pydantic용)
class JobInterestEnum(str, Enum):
    office = "사무"              # 사무
    service = "서비스"           # 서비스
    tech = "기술직"              # 기술직
    education = "교육/강사"       # 교육/강사
    public = "서울시 공공일자리"   # 서울시 공공일자리
    driver = "운전/배송"          # 운전/배송
    etc = "기타"                 # 기타 (직접입력)

# 사용자 기본 필드 (공통으로 사용하는 필드)
class UserBase(BaseModel):
    name: str                      # 사용자 이름
    email: EmailStr                # 이메일
    phone_number: Optional[str] = None  # 전화번호 (선택)
    birthday: Optional[str] = None      # 생년월일
    gender: Optional[str] = None          # 성별
    interests: Optional[JobInterestEnum] = None  # 관심 분야 (Enum 사용)
    custom_interest: Optional[str] = None        # 관심 분야가 '기타'인 경우 직접 입력한 값
    signup_purpose: Optional[str] = None  # 가입 목적
    referral_source: Optional[str] = None  # 유입 경로

    @model_validator(mode="after")
    def validate_interests(cls, model):
        # 만약 interests에 '기타'가 선택되었다면 custom_interest 필드 필수
        if model.interests == JobInterestEnum.etc and not model.custom_interest:
            raise ValueError("관심분야가 '기타'인 경우, custom_interest 필드를 입력해야 합니다.")
        return model

# 회원 가입 시 사용하는 스키마 (비밀번호 포함)
class UserCreate(UserBase):
    password: str   # 반드시 입력해야 하는 비밀번호

# 사용자 정보 수정 시 사용하는 스키마 (모든 필드는 선택적)
class UserUpdate(BaseModel):
    name: Optional[str] = None  # 사용자 이름
    phone_number: Optional[str] = None   # 전화번호
    birthday: Optional[str] = None  # 생년월일
    gender: Optional[str] = None  # 성별
    interests: Optional[JobInterestEnum] = None  # 관심분야 (Enum 사용)
    custom_interest: Optional[str] = None # 관심 분야가 '기타'인 경우
    signup_purpose: Optional[str] = None  # 가입 목적
    referral_source: Optional[str] = None  # 유입 경로

    @model_validator(mode="after")
    def validate_interests(cls, model):   # 관심분야가 '기타' 일시 반드시 입력되어야함
        if model.interests == JobInterestEnum.etc and not model.custom_interest:
            raise ValueError("관심분야가 '기타'인 경우, custom_interest 필드를 입력해야 합니다.")
        return model  # 검증 완료시 모델 반환

class UserUpdateRequest(UserUpdate):
    new_password: Optional[str] = None   # 새 비밀번호
    confirm_password: Optional[str] = None   # 새 비밀번호 확인


# 사용자 조회 시 반환할 스키마 (ORM 모드 활성화)
class UserRead(UserBase):
    id: int  # 사용자 고유 ID
    created_at: datetime  # 생성일
    updated_at: datetime  # 수정일

    class Config:
        orm_mode = True  # ORM 객체 자동 변환