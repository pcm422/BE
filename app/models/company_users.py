from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship

# 유틸리티 함수 임포트
from app.core.datetime_utils import get_now_utc
from app.models.base import Base


# 기업 회원 계정 모델
class CompanyUser(Base):
    __tablename__ = "company_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True)  # 로그인 이메일
    password = Column(String(128), nullable=False)  # 비밀번호
    is_active = Column(Boolean, nullable=False, default=False)  # 이메일 활성상태
    company_id = Column(
        Integer, ForeignKey("company_info.id"), nullable=False
    )  # 참조 기업 ID

    created_at = Column(
        DateTime(timezone=True), # timezone=True 추가
        default=get_now_utc # 유틸리티 함수 사용
    )  # 가입 날짜
    updated_at = Column(
        DateTime(timezone=True), # timezone=True 추가
        default=get_now_utc, # 유틸리티 함수 사용
        onupdate=get_now_utc # 유틸리티 함수 사용
    )  # 수정 날짜

    job_postings = relationship("JobPosting", back_populates="author",lazy="selectin")
    company = relationship("CompanyInfo", back_populates="company_users",lazy="selectin")
    company_name = association_proxy("company", "company_name")

    def __str__(self):
        return self.email
