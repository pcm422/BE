import io
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.db import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from tests.conftest import TEST_DATABASE_URL
from app.models.base import Base

@pytest.mark.asyncio
async def test_job_posting_crud_flow(async_client):
    # joint_test DB에 테이블 생성
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    TestingSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with TestingSessionLocal() as session:
        async def override_get_db():
            yield session
        app.dependency_overrides[get_db_session] = override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            unique_email = f"company_{uuid.uuid4().hex[:8]}@example.com"
            # 1. 회사 생성
            company_data = {
                "name": "테스트 회사",
                "registration_number": "123-45-67890",
                "address": "서울시 테스트구",
                "phone": "010-1234-5678",
                "email": unique_email,
                "password": "testpassword",
                "confirm_password": "testpassword",
                "manager_name": "홍길동",
                "manager_phone": "01099998888",
                "manager_email": "manager@example.com",
                "company_name": "테스트 회사",
                "ceo_name": "대표자",
                "opening_date": "20200101",
                "business_reg_number": "1234567890",
                "company_intro": "테스트 회사 소개입니다."
            }
            resp = await async_client.post("/company/register", json=company_data)
            assert resp.status_code == 201 or resp.status_code == 200    

            # 3. 로그인 및 토큰 획득
            login_data = {"email": unique_email, "password": company_data["password"]}
            resp = await async_client.post("/company/login", json=login_data)
            assert resp.status_code == 200
            token = resp.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 임시 이미지 파일 생성 (in-memory)
            image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            image_file = io.BytesIO(image_content)
            image_file.name = "test.png"  # 파일 이름 지정

            # 4. 채용공고 생성
            job_posting_data = {
                "title": "테스트 공고",
                "recruit_period_start": str(__import__('datetime').date.today()),
                "recruit_period_end": str(__import__('datetime').date.today() + __import__('datetime').timedelta(days=30)),
                "is_always_recruiting_str": "False",
                "education": "대졸",
                "recruit_number": "1",
                "benefits": "4대보험",
                "preferred_conditions": "테스트 코드 작성",
                "other_conditions": "긍정적인 태도",
                "work_address": "서울시 테스트구 테스트동",
                "work_place_name": "테스트 베이스 주식회사",
                "payment_method": "연봉",
                "job_category": "IT·인터넷",
                "work_duration": "1년 이상",
                "is_work_duration_negotiable_str": "False",
                "career": "3년 이상",
                "employment_type": "정규직",
                "salary": "60000000",
                "work_days": "주 5일(월~금)",
                "is_work_days_negotiable_str": "False",
                "is_schedule_based_str": "False",
                "work_start_time": "09:30",
                "work_end_time": "18:30",
                "is_work_time_negotiable_str": "False",
                "description": "상세 설명입니다.",
                "summary": "요약글입니다.",
                "latitude": "37.5665",
                "longitude": "126.9780",
            }

            # files 파라미터에 이미지 파일 추가
            files = {
                "image_file": ("test.png", image_file, "image/png")
            }

            resp = await async_client.post(
                "/posting/",
                data=job_posting_data,
                files=files,
                headers=headers
            )
            assert resp.status_code == 201
            job_id = resp.json()["id"]

            # 5. 채용공고 상세 조회
            resp = await async_client.get(f"/posting/{job_id}")
            assert resp.status_code == 200
            assert resp.json()["title"] == "테스트 공고"

            # 6. 채용공고 목록 조회
            resp = await async_client.get("/posting/")
            assert resp.status_code == 200
            assert any(j["id"] == job_id for j in resp.json()["items"])

            # 7. 채용공고 수정
            update_data = {"title": "수정된 공고 제목", "salary": 65000000}
            resp = await async_client.patch(f"/posting/{job_id}", json=update_data, headers=headers)
            assert resp.status_code == 200
            assert resp.json()["title"] == "수정된 공고 제목"
            assert resp.json()["salary"] == 65000000

            # 8. 채용공고 삭제
            resp = await async_client.delete(f"/posting/{job_id}", headers=headers)
            assert resp.status_code == 204

            # 9. 삭제 후 상세 조회 (존재하지 않아야 함)
            resp = await async_client.get(f"/posting/{job_id}")
            assert resp.status_code == 404

        app.dependency_overrides.clear()