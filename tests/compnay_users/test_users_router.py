
import pytest
from fastapi import FastAPI, Depends, HTTPException, status
from starlette.testclient import TestClient

from app.domains.company_users.router import router as users_router
from app.domains.company_users.schemas import (
    CompanyUserRegisterRequest,
    CompanyUserRegisterResponse,
    CompanyUserLoginRequest,
    CompanyUserLoginResponse,
    FindCompanyUserEmail,
    ResetCompanyUserPassword,
    CompanyTokenRefreshRequest,
)
from app.core.db import get_db_session
from app.core.utils import get_current_company_user

# 더미 DB 세션, 더미 유저
class DummySession:
    pass

class DummyUser:
    id = 7
    email = "u@co.com"
    company_name = "Co"
    # get_company_user_mypage 반환 형태에 맞춰 임의 속성 추가
    def __init__(self):
        self.id = DummyUser.id

# FastAPI app + 의존성 오버라이드
@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(users_router)
    app.dependency_overrides[get_db_session] = lambda: DummySession()
    app.dependency_overrides[get_current_company_user] = lambda: DummyUser()
    return app

@pytest.fixture
def client(app):
    return TestClient(app)

def test_register_companyuser(monkeypatch, client):
    """POST /company/register"""
    async def fake_register(db, payload):
        class CU:
            id = 42
            email = payload.email
            company_name = payload.company_name
        return CU()
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
        "company_intro": "소개글입니다.",
        "password": "pass1234",
        "confirm_password": "pass1234"
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
            id = 5
            email = email
            company = type("X", (), {"company_name": "Co"})
        return U()
    monkeypatch.setattr(
        "app.domains.company_users.router.login_company_user",
        fake_login,
    )
    # 토큰 생성도 패치
    monkeypatch.setattr(
        "app.domains.company_users.router.create_access_token",
        lambda data: "ATOKEN",
    )
    monkeypatch.setattr(
        "app.domains.company_users.router.create_refresh_token",
        lambda data: "RTOKEN",
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
        return {"company_user_id": user.id, "email": user.email}
    monkeypatch.setattr(
        "app.domains.company_users.router.get_company_user_mypage",
        fake_mypage,
    )
    r = client.get("/company/me")
    assert r.status_code == 200
    assert r.json()["data"]["company_user_id"] == DummyUser.id

def test_patch_me(monkeypatch, client):
    """PATCH /company/me"""
    async def fake_update(db, payload, user):
        return {"company_user_id": user.id, "manager_name": payload.manager_name}
    monkeypatch.setattr(
        "app.domains.company_users.router.update_company_user",
        fake_update,
    )
    r = client.patch("/company/me", json={"manager_name": "새매니저"})
    assert r.status_code == 200
    assert r.json()["data"]["manager_name"] == "새매니저"

def test_delete_me(monkeypatch, client):
    """DELETE /company/me"""
    async def fake_delete(db, user):
        return {"company_user_id": user.id}
    monkeypatch.setattr(
        "app.domains.company_users.router.delete_company_user",
        fake_delete,
    )
    r = client.delete("/company/me")
    assert r.status_code == 200
    assert r.json()["data"]["company_user_id"] == DummyUser.id

def test_find_email(monkeypatch, client):
    """POST /company/find-email"""
    async def fake_find(db, payload):
        return {"email": "found@co.com", "company_name": "FCo"}
    monkeypatch.setattr(
        "app.domains.company_users.router.find_company_user_email",
        fake_find,
    )
    body = {"business_reg_number": "123", "opening_date": "20200101", "ceo_name": "홍대표"}
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
        "business_reg_number": "123", "opening_date": "20200101",
        "ceo_name": "홍대표", "email": "u@co.com",
        "new_password": "newpass", "confirm_password": "newpass"
    }
    r = client.post("/company/reset-password", json=body)
    assert r.status_code == 200
    assert r.json()["data"]["email"] == "found@co.com"

def test_refresh_token(monkeypatch, client):
    """POST /company/auth/refresh-token"""
    async def fake_refresh(db, payload):
        return {"access_token": "NEWAT"}
    monkeypatch.setattr(
        "app.domains.company_users.router.refresh_company_user_access_token",
        fake_refresh,
    )
    body = {"refresh_token": "rtoken"}
    r = client.post("/company/auth/refresh-token", json=body)
    assert r.status_code == 200
    assert r.json()["data"]["access_token"] == "NEWAT"
