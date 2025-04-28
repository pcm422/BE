import pytest
from datetime import date, timedelta
from app.domains.company_users.schemas import CompanyUserRegisterRequest
from app.domains.company_users.service import register_company_user
from app.domains.job_postings.schemas import JobPostingCreate, JobPostingUpdate
from app.domains.job_postings import service as job_service
import io
from starlette.datastructures import UploadFile, Headers

@pytest.mark.asyncio
async def test_job_posting_service_crud(db_session, monkeypatch):
    # 1. upload_image_to_ncp mock 처리
    async def fake_upload_image_to_ncp(file, folder):
        return "https://fake-url.com/test.png"
    monkeypatch.setattr(
        "app.core.utils.upload_image_to_ncp",  # 실제 함수 경로
        fake_upload_image_to_ncp
    )

    # 2. 회사/유저 생성
    company_data = CompanyUserRegisterRequest(
        email="company2@example.com",
        password="testpassword",
        confirm_password="testpassword",
        manager_name="홍길동",
        manager_phone="01099998888",
        manager_email="manager2@example.com",
        company_name="테스트 회사2",
        ceo_name="대표자",
        opening_date="2020-01-01",
        business_reg_number="123-45-67690",
        company_intro="테스트 회사 소개입니다."
    )
    company_user = await register_company_user(db_session, company_data)
    author_id = company_user.id
    company_id = company_user.company_id

    # 3. 채용공고 생성
    posting_data = JobPostingCreate(
        title="테스트 공고",
        recruit_period_start=date.today(),
        recruit_period_end=date.today() + timedelta(days=30),
        is_always_recruiting=False,
        education="대졸",
        recruit_number=1,
        benefits="4대보험",
        preferred_conditions="테스트 코드 작성",
        other_conditions="긍정적인 태도",
        work_address="서울시 테스트구 테스트동",
        work_place_name="테스트 베이스 주식회사",
        payment_method="연봉",
        job_category="IT·인터넷",
        work_duration="1년 이상",
        is_work_duration_negotiable=False,
        career="3년 이상",
        employment_type="정규직",
        salary=60000000,
        work_days="주 5일(월~금)",
        is_work_days_negotiable=False,
        is_schedule_based=False,
        work_start_time="09:30",
        work_end_time="18:30",
        is_work_time_negotiable=False,
        description="상세 설명입니다.",
        summary="요약글입니다.",
        latitude=37.5665,
        longitude=126.9780,
        postings_image="test.png"
    )

    # 임시 이미지 파일 생성
    image_content = b"test"
    headers = Headers({"content-type": "image/png"})
    image_file = UploadFile(
        filename="test.png",
        file=io.BytesIO(image_content),
        headers=headers
    )

    posting = await job_service.create_job_posting(
        db_session, posting_data, author_id, company_id, image_file=image_file
    )
    assert posting.id is not None
    assert posting.title == "테스트 공고"

    # 4. 상세 조회
    found = await job_service.get_job_posting(db_session, posting.id)
    assert found is not None
    assert found.title == "테스트 공고"

    # 5. 목록 조회
    postings, total = await job_service.list_job_postings(db_session)
    assert total >= 1
    assert any(p.id == posting.id for p in postings)

    # 6. 수정
    update_data = JobPostingUpdate(title="수정된 공고 제목", salary=65000000)
    updated = await job_service.update_job_posting(db_session, posting.id, update_data)
    assert updated.title == "수정된 공고 제목"
    assert updated.salary == 65000000

    # 7. 삭제
    deleted = await job_service.delete_job_posting(db_session, posting.id)
    assert deleted is True

    # 8. 삭제 후 상세 조회
    not_found = await job_service.get_job_posting(db_session, posting.id)
    assert not_found is None
