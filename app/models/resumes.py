from datetime import date

from pydantic import field_validator
from sqlalchemy import Column, Date, DateTime
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.datetime_utils import get_now_kst
from app.models import Base


class Resume(Base):
    __tablename__ = "resumes"  # 테이블 이름
    id = Column(Integer, primary_key=True, index=True)  # 고유 식별자
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # FK = user.id
    resume_image = Column(String(255), nullable=True)  # 이력서 사진
    desired_area = Column(String(255), nullable=True)  # 희망 지역
    introduction = Column(Text, nullable=True)  # 자기소개
    created_at = Column(DateTime(timezone=True), default=get_now_kst)  # 생성일
    updated_at = Column(DateTime(timezone=True), default=get_now_kst, onupdate=get_now_kst)  # 수정일

    # 관계
    user = relationship("User", back_populates="resumes", lazy="selectin")
    educations = relationship(
        "ResumeEducation",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        passive_deletes=True
    )

    experiences = relationship(
        "ResumeExperience",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        passive_deletes=True
    )

    applications = relationship(
        "JobApplication",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_month_only(cls, value):
        # 예: '2023-06' → '2023-06-01'
        if value:
            return date.fromisoformat(f"{value}-01")
        return None

    def __str__(self):
        return f"{self.id} - {self.created_at}"