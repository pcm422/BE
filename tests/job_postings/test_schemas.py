import pytest
from datetime import date
from app.domains.job_postings.schemas import JobPostingCreate
from app.models.job_postings import EducationEnum, PaymentMethodEnum, JobCategoryEnum


def test_job_posting_create_valid():
    data = {
        "title": "백엔드 개발자 모집",
        "education": EducationEnum.college_4,  # 실제 Enum 멤버 사용
        "recruit_number": 2,
        "work_address": "서울시 강남구",
        "work_place_name": "테스트회사",
        "payment_method": PaymentMethodEnum.monthly,  # 실제 Enum 멤버 사용
        "job_category": JobCategoryEnum.it,  # 실제 Enum 멤버 사용
        "career": "신입",
        "employment_type": "정규직",
        "salary": 3500000,
        "recruit_period_start": date.today(),
        "recruit_period_end": date.today(),
    }
    schema = JobPostingCreate(**data)
    assert schema.title == data["title"]
    assert schema.salary == data["salary"]


def test_job_posting_create_invalid_salary():
    data = {
        "title": "프론트엔드 개발자",
        "education": EducationEnum.college_4,  # 실제 Enum 멤버 사용
        "recruit_number": 1,
        "work_address": "서울시 강남구",
        "work_place_name": "테스트회사",
        "payment_method": PaymentMethodEnum.monthly,  # 실제 Enum 멤버 사용
        "job_category": JobCategoryEnum.it,  # 실제 Enum 멤버 사용
        "career": "경력",
        "employment_type": "계약직",
        "salary": -1000,
    }
    with pytest.raises(ValueError):
        JobPostingCreate(**data)