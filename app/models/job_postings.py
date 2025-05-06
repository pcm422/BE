from enum import Enum

from sqlalchemy import Boolean, Column, Date, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import relationship

# 유틸리티 함수 임포트
from app.core.datetime_utils import get_now_utc
from app.models.base import Base


class EducationEnum(str, Enum):
    none = "학력 무관"
    high = "고졸"
    college_2 = "초대졸"
    college_4 = "대졸"
    graduate = "대학원"


class PaymentMethodEnum(str, Enum):
    hourly = "시급"
    daily = "일급"
    weekly = "주급"
    monthly = "월급"
    yearly = "연봉"


class JobCategoryEnum(str, Enum):
    food = "외식·음료"
    sales = "유통·판매"
    culture = "문화·여가·생활"
    service = "서비스"
    admin = "사무·회계"
    cs = "고객상담·영업·리서치"
    labor = "생산·건설·노무"
    it = "IT·인터넷"
    education = "교육·강사"
    design = "디자인"
    media = "미디어"
    delivery = "운전·배달"
    medical = "병원·간호·연구"
    pro_consult = "전문-상담직"
    pro_admin = "전문-사무직"
    pro_bar = "전문-BAR"
    pro_labor = "전문-생산직"
    pro_food = "전문-외식업"


class WorkDurationEnum(str, Enum):
    more_3_months = "3개월 이상"
    between_3_6_months = "3개월 ~ 6개월"
    more_6_months = "6개월 이상"
    between_6_12_months = "6개월 ~ 1년"
    more_1_year = "1년 이상"
    between_1_3_years = "1년 ~ 3년"
    more_3_years = "3년 이상"


class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True)
    title = Column(String(50), nullable=False)

    author_id = Column(Integer, ForeignKey("company_users.id", ondelete='CASCADE'))  # 담당자
    company_id = Column(Integer, ForeignKey("company_info.id", ondelete='CASCADE'))  # 회사

    recruit_period_start = Column(Date, nullable=True)
    recruit_period_end = Column(Date, nullable=True)
    is_always_recruiting = Column(Boolean, default=False)

    education = Column(
        SQLAlchemyEnum(EducationEnum, name="education_enum"), nullable=False
    )
    recruit_number = Column(Integer, nullable=False)
    benefits = Column(Text)
    preferred_conditions = Column(Text)
    other_conditions = Column(Text)

    work_address = Column(String(255), nullable=False)
    work_place_name = Column(String(25), nullable=False)
    region1 = Column(String(50), nullable=True)
    region2 = Column(String(50), nullable=True)

    payment_method = Column(
        SQLAlchemyEnum(PaymentMethodEnum, name="payment_method_enum"), nullable=False
    )
    job_category = Column(
        SQLAlchemyEnum(JobCategoryEnum, name="job_category_enum"), nullable=False
    )
    work_duration = Column(SQLAlchemyEnum(WorkDurationEnum, name="work_duration_enum"))
    is_work_duration_negotiable = Column(Boolean, default=False)
    career = Column(String(50), nullable=False)
    employment_type = Column(String(50), nullable=False)
    salary = Column(Integer, nullable=False)

    work_days = Column(String(255), nullable=True)
    is_work_days_negotiable = Column(Boolean, default=False)
    is_schedule_based = Column(Boolean, default=False)

    work_start_time = Column(String(5), nullable=True)
    work_end_time = Column(String(5), nullable=True)
    is_work_time_negotiable = Column(Boolean, default=False)

    description = Column(Text, nullable=True)
    summary = Column(String(255), nullable=True)
    postings_image = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), default=get_now_utc)
    updated_at = Column(DateTime(timezone=True), default=get_now_utc, onupdate=get_now_utc)

    # 관계 설정
    author = relationship("CompanyUser", back_populates="job_postings")
    company = relationship("CompanyInfo", back_populates="job_postings")
    favorites = relationship(
        "Favorite", back_populates="job_posting", cascade="all, delete-orphan"
    )
    applications = relationship(
        "JobApplication", back_populates="job_posting", cascade="all, delete-orphan"
    )

    def __str__(self):
        return self.title
