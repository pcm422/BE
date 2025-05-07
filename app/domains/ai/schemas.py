from typing import Optional

from pydantic import BaseModel

class AIJobPostSchema(BaseModel):
    title: str
    job_category: str
    education: str
    employment_type: str
    payment_method: str
    salary: int
    work_duration: Optional[str]
    is_work_duration_negotiable: bool
    work_days: Optional[str]
    is_work_days_negotiable: bool
    work_start_time: Optional[str]
    work_end_time: Optional[str]
    is_work_time_negotiable: bool
    career: str
    work_place_name: str
    work_address: str
    benefits: Optional[str]
    preferred_conditions: Optional[str]
    description: Optional[str]

class SummarizeResponse(BaseModel):
    summary: str