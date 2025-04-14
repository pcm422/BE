from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import relationship

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
    created_at = Column(DateTime, default=datetime.now)  # 생성일
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)  # 수정일

    # 관계
    resume = relationship("Resume", back_populates="educations")


    def __str__(self):
        return f"{self.school_name} - {self.education_type}"