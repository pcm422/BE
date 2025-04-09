from pydantic import BaseModel, EmailStr, ConfigDict

# 공통 속성 정의 (다른 스키마에서 상속받아 사용)
class UserBase(BaseModel):
    email: EmailStr # Pydantic의 EmailStr 타입으로 이메일 형식 검증

# 유저 생성 시 요청 본문 스키마
class UserCreate(UserBase):
    password: str # 비밀번호는 생성 시에만 받음

# 유저 조회 등 응답 시 사용될 스키마
class User(UserBase):
    id: int # 응답에는 유저 ID 포함

    # SQLAlchemy 모델 객체를 Pydantic 스키마로 변환 가능하게 설정
    model_config = ConfigDict(from_attributes=True)