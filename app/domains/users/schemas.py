from typing import List, Optional

from pydantic import BaseModel, Field


# 회원가입 요청에 대한 스키마 클래스
class UserRegister(BaseModel):
    name: str = Field(
        ..., max_length=50, description="사용자 이름 (최대 50자)"
    )  # 이름: 필수, 최대 50자
    email: str = Field(
        ..., description="중복 불가 이메일"
    )  # 이메일: 필수, 중복 체크 필요
    password: str = Field(
        ..., description="비밀번호 (서버에서 해시 처리)"
    )  # 비밀번호: 필수, 해시 처리 예정
    phone_number: Optional[str] = Field(
        None, description="전화번호"
    )  # 전화번호: 선택 사항
    birthday: Optional[str] = Field(
        None, description="생년월일 (YYYY-MM-DD)"
    )  # 생년월일: 선택 사항
    gender: Optional[str] = Field(
        None, description="성별 (남성 또는 여성)"
    )  # 성별: 선택 사항
    interests: Optional[List[str]] = Field(
        None, description="관심 분야 리스트"
    )  # 관심분야: 문자열 리스트, 선택 사항
    signup_purpose: Optional[str] = Field(
        None, description="가입 목적"
    )  # 가입 목적: 선택 사항
    referral_source: Optional[str] = Field(
        None, description="유입 경로"
    )  # 유입 경로: 선택 사항


# 로그인 요청에 대한 스키마 클래스
class UserLogin(BaseModel):
    email: str = Field(..., description="로그인할 이메일")  # 이메일: 필수
    password: str = Field(..., description="비밀번호")  # 비밀번호: 필수


# 사용자 프로필 업데이트(PATCH) 요청 스키마 클래스
class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(
        None, max_length=50, description="사용자 이름 (최대 50자)"
    )  # 이름 업데이트: 선택 사항
    password: Optional[str] = Field(
        None, description="새로운 비밀번호"
    )  # 새로운 비밀번호 업데이트: 선택 사항
    current_password: Optional[str] = Field(
        None, description="현재 비밀번호 (새 비밀번호 변경 시 필요)"
    )  # 현재 비밀번호 입력
    phone_number: Optional[str] = Field(
        None, description="전화번호"
    )  # 전화번호 업데이트: 선택 사항
    birthday: Optional[str] = Field(
        None, description="생년월일 (YYYY-MM-DD)"
    )  # 생년월일 업데이트: 선택 사항
    gender: Optional[str] = Field(
        None, description="성별 (남성 또는 여성)"
    )  # 성별 업데이트: 선택 사항
    interests: Optional[List[str]] = Field(
        None, description="관심 분야 리스트"
    )  # 관심분야 업데이트: 선택 사항
    signup_purpose: Optional[str] = Field(
        None, description="가입 목적"
    )  # 가입 목적 업데이트: 선택 사항
    referral_source: Optional[str] = Field(
        None, description="유입 경로"
    )  # 유입 경로 업데이트: 선택 사항


# 비밀번호 재설정 요청 스키마 클래스
class PasswordResetverify(BaseModel):
    email: str = Field(..., description="이메일")  # 이메일: 필수
    name: str = Field(..., description="사용자 이름")  # 사용자 이름: 필수
    phone_number : str = Field(..., description="전화번호")  # 전화번호 : 필수
    birthday : str = Field(..., description="생년월일")  # 생년월일 : 필수


# 사용자 인증 성공 응답 스키마
class PasswordResetVerifyResponse(BaseModel):
    status: str  # 상태 (success)
    data: dict   # {"user_id": int}


# 비밀번호 재설정 요청용 스키마
class PasswordResetConfirmRequest(BaseModel):
    user_id: int          # 인증 완료된 사용자 ID
    new_password: str     # 새 비밀번호

# 비밀번호 재설정 성공 응답 스키마
class PasswordResetConfirmResponse(BaseModel):
    status: str  # 상태 (success)
    message: str  # "비밀번호가 재설정되었습니다."


# 리프레쉬 토큰을 사용한 액세스 토큰 재발급 요청 스키마 클래스
class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="리프레쉬 토큰")  # 리프레쉬 토큰: 필수

# 이메일 찾는 스키마
class FindEmailRequest(BaseModel):
    name: str
    phone_number: str
    birthday: str  # "YYYY-MM-DD"