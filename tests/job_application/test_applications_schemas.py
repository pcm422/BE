import pytest
from pydantic import ValidationError
from datetime import datetime

from app.domains.job_applications.schemas import (
    ResumeApplyCreate, JobApplicationStatusUpdate, JobApplicationRead, JobPostingSummary
)
from app.models.job_applications import ApplicationStatusEnum


def test_resume_apply_create_valid():
    """
    ResumeApplyCreate 스키마의 유효한 데이터 검증
    """
    data = {"job_posting_id": 123}
    model = ResumeApplyCreate(**data)
    assert model.job_posting_id == 123  # 필드 값 검증


def test_resume_apply_create_invalid():
    """
    잘못된 데이터 입력 시 ValidationError 발생
    """
    with pytest.raises(ValidationError):
        ResumeApplyCreate(**{})  # 필수 필드 누락


def test_status_update_valid():
    """
    JobApplicationStatusUpdate 스키마의 올바른 상태 값 검증
    """
    model = JobApplicationStatusUpdate(status=ApplicationStatusEnum.passed)
    assert model.status == ApplicationStatusEnum.passed  # 상태 값 검증


def test_job_application_read_from_orm():
    """
    JobApplicationRead 모델이 ORM 객체로부터 생성되는지 테스트
    """
    # Create a JobPostingSummary Pydantic model instance for nested data
    posting_summary = JobPostingSummary(
        title="T1",
        company_id=2,
        recruit_period_start=datetime(2025, 5, 1),
        recruit_period_end=datetime(2025, 6, 1),
        work_address="서울",
        work_place_name="본사",
    )

    # Create a dummy ORM-like object with attributes matching JobApplicationRead
    orm_obj = type(
        "O", (), {
            "id": 1,
            "user_id": 2,
            "job_posting_id": 3,
            "job_posting": posting_summary,
            "resumes_data": {},
            "status": ApplicationStatusEnum.applied,
            "email_sent": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    )()

    # Validate using Pydantic V2's model_validate
    model = JobApplicationRead.model_validate(orm_obj)
    assert model.id == 1  # ID 검증
    assert model.job_posting.title == "T1"  # nested 필드 검증
