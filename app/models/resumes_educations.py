from datetime import date
from enum import Enum as PyEnum

from pydantic import field_validator
from sqlalchemy import Column, Date, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.datetime_utils import get_now_kst
from app.models import Base


class EducationTypeEnum(str, PyEnum):
    high_school = "고등학교"
    college_2_3 = "대학교(2,3년)"
    college_4 = "대학교(4년)"
    graduate = "대학원"


class EducationStatusEnum(str, PyEnum):
    graduated = "졸업"
    studying = "재학중"
    on_leave = "휴학"
    expected = "예정"


class ResumeEducation(Base):
    __tablename__ = "resumes_educations"  # 테이블 이름
    id = Column(Integer, primary_key=True, index=True)  # 고유 식별자
    resumes_id = Column(
        Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )  # FK = resumes.id
    education_type = Column(
        SQLEnum(EducationTypeEnum, name="educationtype"), nullable=True
    )  # 학교 타입
    school_name = Column(String(255), nullable=True)  # 학교명
    education_status = Column(
        SQLEnum(EducationStatusEnum, name="educationstatus"), nullable=True
    )  # 학력 상태
    start_date = Column(Date, nullable=True)  # 입학일
    end_date = Column(Date, nullable=True)  # 졸업(예정)일
    created_at = Column(DateTime(timezone=True), default=get_now_kst)  # 생성일
    updated_at = Column(DateTime(timezone=True), default=get_now_kst, onupdate=get_now_kst)  # 수정일

    # 관계
    resume = relationship("Resume", back_populates="educations", lazy="selectin")


    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_month_only(cls, value):
        # 예: '2023-06' → '2023-06-01'
        if value:
            return date.fromisoformat(f"{value}-01")
        return None

    def __str__(self):
        return f"{self.school_name} - {self.education_type}"