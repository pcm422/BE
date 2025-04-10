from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from app.models import Base


class GenderEnum(str, PyEnum):
    male = "남성"
    female = "여성"

class JobInterestEnumSQL(str, PyEnum):
    office = "사무"  # 사무 분야
    service = "서비스"  # 서비스 분야
    tech = "기술직"  # 기술 분야
    education = "교육/강사"  # 교육 및 강사 분야
    public = "서울시 공공일자리"  # 서울시 공공일자리 분야
    driver = "운전/배송"  # 운전 및 배송 분야
    etc = "기타"  # 기타 (직접 입력 가능)


class User(Base):
    __tablename__ = "users"  # 테이블 이름
    id = Column(Integer, primary_key=True, index=True)  # 고유 식별자
    name = Column(String(50), nullable=False)  # 이름 (최대 50자)
    email = Column(String(255), nullable=False, unique=True, index=True)  # 이메일
    user_image = Column(String(255), nullable=True)  # 이미지 url
    password = Column(String(255), nullable=False)  # 비밀번호
    phone_number = Column(String(50), nullable=True)  # 전화번호
    birthday = Column(String(50), nullable=True)  # 생년월일
    gender = Column(SQLEnum(GenderEnum,name="genderenum",values_callable=lambda enum: [member.value for member in enum]),nullable=True)
    interests = Column(SQLEnum(JobInterestEnumSQL, name="jobinterest_enum"), nullable=True)  # 관심분야
    custom_interest = Column(String, nullable=True)  # 관심분야가 '기타'일경우
    signup_purpose = Column(Text, nullable=True)  # 가입 목적
    referral_source = Column(Text, nullable=True)  # 유입경로
    is_active = Column(Boolean, nullable=False, default=False)  # 이메일 활성상태
    created_at = Column(DateTime, default=datetime.now)  # 생성일
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)  # 수정일

    # 관계
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("JobApplication", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")