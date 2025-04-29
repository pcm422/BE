import pytest
from fastapi import Depends, FastAPI, HTTPException
from starlette.testclient import TestClient

from app.core.db import get_db_session
from app.domains.company_info.router import router as company_router
from app.domains.company_info.schemas import PublicCompanyInfo


# 더미 DB 세션 픽스처
@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(company_router)

    # get_db_session 의존성 대체
    async def fake_db_session():
        yield None

    app.dependency_overrides[get_db_session] = fake_db_session
    return app


def test_get_companyinfo_success(monkeypatch, app):
    """GET /companies/{id} 성공 케이스"""
    dummy = PublicCompanyInfo(
        company_id=1,
        company_name="테스트사",
        company_intro="소개",
        business_reg_number="1234567890",
        opening_date="20200101",
        ceo_name="홍길동",
        manager_name="김매니저",
        manager_phone="01012345678",
        manager_email="mgr@test.com",
        address=None,
        company_image=None,
        job_postings=[],
    )

    async def fake_service(db, company_id: int):
        return dummy

    monkeypatch.setattr(
        "app.domains.company_info.router.get_company_info",
        fake_service,
    )

    client = TestClient(app)
    r = client.get("/companies/1")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["data"]["company_id"] == 1
    assert body["data"]["company_name"] == "테스트사"


def test_get_companyinfo_not_found(monkeypatch, app):
    """GET /companies/{id} 404 케이스"""

    async def fake_service(db, company_id: int):
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    monkeypatch.setattr(
        "app.domains.company_info.router.get_company_info",
        fake_service,
    )

    client = TestClient(app)
    r = client.get("/companies/999")
    assert r.status_code == 404
    assert r.json()["detail"] == "기업 정보를 찾을 수 없습니다."
