from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


# 기업 회원 계정 모델
class CompanyUser(Base):
    __tablename__ = "company_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True)  # 로그인 이메일
    password = Column(String(128), nullable=False)  # 비밀번호
    company_id = Column(
        Integer, ForeignKey("company_info.id"), nullable=False
    )  # 참조 기업 ID
    manager_name = Column(String(50), nullable=False)  # 담당자 이름
    manager_phone = Column(String(20), nullable=False)  # 담당자 전화번호
    manager_email = Column(String(100), nullable=True)  # 담당자 이메일
    created_at = Column(DateTime, default=datetime.now)  # 가입 날짜
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )  # 수정 날짜

    job_postings = relationship("JobPosting", back_populates="author",lazy="selectin")
    company = relationship("CompanyInfo", back_populates="company_users",lazy="selectin")

    def __str__(self):
        return self.email
