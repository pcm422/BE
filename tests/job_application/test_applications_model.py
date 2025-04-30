import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import date

from app.models import JobApplication, Resume, JobPosting, User, CompanyInfo, CompanyUser
from app.models.job_applications import ApplicationStatusEnum
from app.models.job_postings import WorkDurationEnum, JobCategoryEnum, PaymentMethodEnum, EducationEnum


@pytest.mark.asyncio
async def test_model_create_and_query(db_session: AsyncSession):
    """
    JobApplication 모델의 생성 및 조회 기능 테스트
    """
    # 사용자 및 공고, 이력서 생성
    user = User(name="A", email="a@test.com", password="pwd")
    db_session.add(user)
    await db_session.commit()
    # 기업 정보 및 기업 유저 생성
    company = CompanyInfo(
        company_name="테스트기업",
        ceo_name="홍대표",
        business_reg_number="1234567890",
        opening_date="2020-01-01",
        company_intro="테스트 기업 소개",
        manager_name="김담당",
        manager_phone="01012345678",
        manager_email="hr@test.com"
    )
    db_session.add(company)
    await db_session.flush()  # company.id 확보

    company_user = CompanyUser(
        email="corp@test.com",
        password="pwd",
        company_id=company.id
    )
    db_session.add(company_user)
    await db_session.flush()  # company_user.id 확보

    posting = JobPosting(
        title="T",
        company_id=company.id,
        author_id=company_user.id,
        recruit_period_start=date(2025, 5, 1),
        recruit_period_end=date(2025, 6, 1),
        is_always_recruiting=False,
        education=EducationEnum.college_4,
        recruit_number=1,
        payment_method=PaymentMethodEnum.monthly,
        job_category=JobCategoryEnum.it,
        work_duration=WorkDurationEnum.more_6_months,
        is_work_duration_negotiable=False,
        career="무관",
        employment_type="정규직",
        salary=3000,
        work_days="월~금",
        is_work_days_negotiable=False,
        is_schedule_based=False,
        work_address="서울시 강남구",
        work_place_name="본사",
        is_work_time_negotiable=False,
        postings_image="https://example.com/default.png",
    )
    db_session.add(posting)
    await db_session.commit()
    resume = Resume(user_id=user.id)  # 빈 이력서 데이터로 초기화
    db_session.add(resume)
    await db_session.commit()

    # JobApplication 생성
    app = JobApplication(
        user_id=user.id,
        job_posting_id=posting.id,
        resume_id=resume.id,
        resumes_data={},
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    assert app.status == ApplicationStatusEnum.applied  # 기본 상태 검증
    assert app.resume_id == resume.id  # 외래키 연결 검증