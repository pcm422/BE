from datetime import datetime

from sqlalchemy import Column, Date, DateTime
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models import Base


class Resume(Base):
    __tablename__ = "resumes"  # 테이블 이름
    id = Column(Integer, primary_key=True, index=True)  # 고유 식별자
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # FK = user.id
    resume_image = Column(String(255), nullable=True)  # 이력서 사진
    company_name = Column(String(255), nullable=True)  # 이전회사명
    position = Column(String(255), nullable=True)  # 직급/직무
    work_period_start = Column(Date, nullable=True)  # 근무 시작일
    work_period_end = Column(Date, nullable=True)  # 근무 종료일 (재직 중일시 Null)
    desired_area = Column(String(255), nullable=True)  # 희망 지역
    introduction = Column(Text, nullable=True)  # 자기소개
    created_at = Column(DateTime, default=datetime.now)  # 생성일
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)  # 수정일

    # 관계
    user = relationship("User", back_populates="resumes", lazy="selectin")
    educations = relationship(
        "ResumeEducation",
        back_populates="resume",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin"
    )


    def __str__(self):
        return f"{self.company_name or '이전 회사 없음'} ({self.position or '직무 없음'})"