# tests/compnay_users/test_users_router.py

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.core.db import get_db_session
from app.core.utils import get_current_company_user
from app.domains.company_users.router import router as users_router


# 더미 DB 세션 (전혀 사용되진 않지만, 의존성 오버라이드용)
class DummySession:
    pass


# 더미 로그인된 유저
class DummyUser:
    def __init__(self):
        self.id = 7
        self.email = "u@co.com"
        # company 속성은 get_me에서 쓰이는 CompanyUserInfo 필드용
        self.company = type(
            "C",
            (),
            {
                "company_name": "CoName",
                "manager_name": "MgrName",
                "manager_phone": "01012345678",
                "manager_email": "mgr@co.com",
                "business_reg_number": "1234567890",
                "opening_date": "20200101",
                "ceo_name": "CEOName",
                "company_intro": "테스트 회사 소개글입니다.",  # 10자 이상
                "address": None,
                "company_image": None,
                "job_postings": [],
            },
        )


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(users_router)
    # DB, 현재 유저 의존성 오버라이드
    app.dependency_overrides[get_db_session] = lambda: DummySession()
    app.dependency_overrides[get_current_company_user] = lambda: DummyUser()
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_register_companyuser(monkeypatch, client):
    """POST /company/register"""

    async def fake_register(db, payload):
        # payload.company_intro 은 10자 이상이어야 통과
        class CU:
            pass

        u = CU()
        u.id = 42
        u.email = payload.email
        u.company_name = payload.company_name
        return u

    monkeypatch.setattr(
        "app.domains.company_users.router.register_company_user",
        fake_register,
    )

    body = {
        "email": "new@co.com",
        "manager_name": "매니저",
        "manager_phone": "01012345678",
        "manager_email": "mgr@co.com",
        "company_name": "NewCo",
        "ceo_name": "홍대표",
        "opening_date": "20200101",
        "business_reg_number": "1234567890",
        "company_intro": "테스트 회사 소개글입니다.",  # 10자 이상
        "password": "pass1234",
        "confirm_password": "pass1234",
    }
    r = client.post("/company/register", json=body)
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["company_user_id"] == 42
    assert data["email"] == "new@co.com"


def test_login_companyuser(monkeypatch, client):
    """POST /company/login"""

    async def fake_login(db, email, password):
        class U:
            pass

        u = U()
        u.id = 5
        u.email = email
        u.company = type("X", (), {"company_name": "Co"})
        return u

    async def fake_create_access_token(data):
        return "ATOKEN"

    async def fake_create_refresh_token(data):
        return "RTOKEN"

    monkeypatch.setattr(
        "app.domains.company_users.router.login_company_user",
        fake_login,
    )
    monkeypatch.setattr(
        "app.domains.company_users.router.create_access_token",
        fake_create_access_token,
    )
    monkeypatch.setattr(
        "app.domains.company_users.router.create_refresh_token",
        fake_create_refresh_token,
    )

    body = {"email": "u@co.com", "password": "pwd"}
    r = client.post("/company/login", json=body)
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["access_token"] == "ATOKEN"
    assert d["refresh_token"] == "RTOKEN"
    assert d["company_user_id"] == 5


def test_logout_companyuser(client):
    """POST /company/logout"""
    r = client.post("/company/logout")
    assert r.status_code == 200
    assert r.json()["message"].startswith("로그아웃")


def test_get_me(monkeypatch, client):
    """GET /company/me"""

    async def fake_mypage(db, user):
        # CompanyUserInfo에 필요한 모든 필드를 채워서 반환해야 검증 통과
        return {
            "company_user_id": user.id,
            "email": user.email,
            "company_id": 1,
            "company_name": user.company.company_name,
            "manager_name": user.company.manager_name,
            "manager_email": user.company.manager_email,
            "manager_phone": user.company.manager_phone,
            "business_reg_number": user.company.business_reg_number,
            "opening_date": user.company.opening_date,
            "ceo_name": user.company.ceo_name,
            "company_intro": user.company.company_intro,
            "address": user.company.address,
            "company_image": user.company.company_image,
            "job_postings": user.company.job_postings,
        }

    monkeypatch.setattr(
        "app.domains.company_users.router.get_company_user_mypage",
        fake_mypage,
    )

    r = client.get("/company/me")
    assert r.status_code == 200
    assert r.json()["data"]["company_user_id"] == 7


def test_patch_me(monkeypatch, client):
    """PATCH /company/me"""

    async def fake_update(db, payload, current_user):
        # CompanyUserUpdateResponse에 필수 필드를 모두 채워서 반환
        return {
            "company_user_id": current_user.id,
            "email": current_user.email,
            "company_name": current_user.company.company_name,
            "manager_name": payload.manager_name,
            "manager_email": current_user.company.manager_email,
            "manager_phone": current_user.company.manager_phone,
            "company_intro": current_user.company.company_intro,
            "address": current_user.company.address,
            "company_image": current_user.company.company_image,
        }

    monkeypatch.setattr(
        "app.domains.company_users.router.update_company_user",
        fake_update,
    )

    r = client.patch("/company/me", json={"manager_name": "새매니저"})
    assert r.status_code == 200
    assert r.json()["data"]["manager_name"] == "새매니저"


def test_delete_me(monkeypatch, client):
    """DELETE /company/me"""

    async def fake_delete(db, current_user):
        return {"company_user_id": current_user.id}

    monkeypatch.setattr(
        "app.domains.company_users.router.delete_company_user",
        fake_delete,
    )

    r = client.delete("/company/me")
    assert r.status_code == 200
    assert r.json()["data"]["company_user_id"] == 7


def test_find_email(monkeypatch, client):
    """POST /company/find-email"""

    async def fake_find(db, payload):
        return {"email": "found@co.com", "company_name": "FCo"}

    monkeypatch.setattr(
        "app.domains.company_users.router.find_company_user_email",
        fake_find,
    )

    body = {
        "business_reg_number": "123",
        "opening_date": "20200101",
        "ceo_name": "홍대표",
    }
    r = client.post("/company/find-email", json=body)
    assert r.status_code == 200
    assert r.json()["data"]["email"] == "found@co.com"


def test_reset_password(monkeypatch, client):
    """POST /company/reset-password"""

    async def fake_reset(db, payload):
        return "found@co.com"

    monkeypatch.setattr(
        "app.domains.company_users.router.reset_company_user_password",
        fake_reset,
    )

    body = {
        "business_reg_number": "123",
        "opening_date": "20200101",
        "ceo_name": "홍대표",
        "email": "u@co.com",
        "new_password": "newpass1",  # 8자 이상
        "confirm_password": "newpass1",
    }
    r = client.post("/company/reset-password", json=body)
    assert r.status_code == 200
    assert r.json()["data"]["email"] == "found@co.com"


def test_refresh_token(monkeypatch, client):
    """POST /company/auth/refresh-token"""

    async def fake_refresh(db, token_data):
        return {"access_token": "NEWAT"}

    monkeypatch.setattr(
        "app.domains.company_users.router.refresh_company_user_access_token",
        fake_refresh,
    )

    body = {"refresh_token": "rtoken"}
    r = client.post("/company/auth/refresh-token", json=body)
    assert r.status_code == 200
    assert r.json()["data"]["access_token"] == "NEWAT"
