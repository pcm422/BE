from sqlalchemy import Column, Date, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base

# 기업 정보 모델 (기업 마이페이지)


class CompanyInfo(Base):
    __tablename__ = "company_info"

    id = Column(Integer, primary_key=True, index=True)  # 기본 키 (자동 증가)
    company_name = Column(String(50), nullable=False)  # 기업명
    business_reg_number = Column(
        String(50), unique=True, nullable=False
    )  # 사업자등록번호
    opening_date = Column(Date, nullable=False)  # 개업 일자 (YYYY-MM-DD 형식)
    company_intro = Column(Text, nullable=False)  # 기업 소개
    ceo_name = Column(String(50), nullable=False)  # 대표자 성함
    address = Column(String(100), nullable=True)  # 사업장 주소 (선택)
    company_image = Column(String(255), nullable=True)  # 회사 이미지 URL (선택)

    job_postings = relationship("JobPosting", back_populates="company",lazy="selectin")
    company_users = relationship("CompanyUser", back_populates="company",lazy="selectin")

    def __str__(self):
        return self.company_name
