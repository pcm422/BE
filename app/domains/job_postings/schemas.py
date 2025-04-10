from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from enum import Enum

class PaymentMethodEnum(str, Enum):
    hourly = "시급"
    daily = "일급"
    monthly = "월급"
    yearly = "연봉"

class EmploymentTypeEnum(str, Enum):
    full_time = "정규직"
    contract = "계약직"
    intern = "인턴"
    freelance = "프리랜서"
    etc = "기타"

class CareerTypeEnum(str, Enum):
    new = "신입"
    experienced = "경력"
    both = "무관"

class JobPostingCreate(BaseModel):
    title: str
    recruit_period_start: date
    recruit_period_end: date
    is_always_recruiting: bool
    education: str
    recruit_number: int
    benefits: Optional[str] = None
    preferred_conditions: Optional[str] = None
    other_conditions: Optional[str] = None
    work_address: str
    work_place_name: str
    payment_method: PaymentMethodEnum
    job_category: str
    work_duration: str
    career: CareerTypeEnum
    employment_type: EmploymentTypeEnum
    salary: int
    deadline_at: date
    work_days: str
    description: str
    
class JobPostingResponse(JobPostingCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True