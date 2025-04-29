

import pytest
from fastapi import FastAPI, HTTPException
from starlette.testclient import TestClient

from app.core.db import get_db_session
from app.core.utils import get_current_company_user
from app.domains.company_users.router import router as users_router
from app.domains.company_users.schemas import (
    PasswordResetVerifyRequest,
)


# 더미 DB 세션 (의존성 오버라이드용)
class DummySession:
    pass


# 더미 로그인된 유저
class DummyUser:
    def __init__(self):
        self.id = 7
        self.email = "u@co.com"
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
        "company_intro": "테스트 회사 소개글입니다.",
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

    r = client.post("/company/login", json={"email": "u@co.com", "password": "pwd"})
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


def test_refresh_token(monkeypatch, client):
    """POST /company/auth/refresh-token"""

    async def fake_refresh(db, token_data):
        return {"access_token": "NEWAT"}

    monkeypatch.setattr(
        "app.domains.company_users.router.refresh_company_user_access_token",
        fake_refresh,
    )
    r = client.post("/company/auth/refresh-token", json={"refresh_token": "rtoken"})
    assert r.status_code == 200
    assert r.json()["data"]["access_token"] == "NEWAT"


# ==== 비밀번호 재설정 라우터 테스트 추가 ====


def test_verify_reset_password_success(monkeypatch, client):
    """POST /company/reset-password/verify 성공"""
    sample_token = "tok"

    async def fake_gen(db, payload):
        assert isinstance(payload, PasswordResetVerifyRequest)
        return sample_token

    monkeypatch.setattr(
        "app.domains.company_users.router.generate_password_reset_token",
        fake_gen,
    )
    body = {
        "business_reg_number": "123",
        "opening_date": "20200101",
        "ceo_name": "CEO",
        "email": "a@b.com",
    }
    r = client.post("/company/reset-password/verify", json=body)
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "success"
    assert j["data"]["reset_token"] == sample_token


def test_verify_reset_password_fail(monkeypatch, client):
    """POST /company/reset-password/verify 검증 실패 → 404"""

    async def fake_err(db, payload):
        raise HTTPException(status_code=404, detail="fail")

    monkeypatch.setattr(
        "app.domains.company_users.router.generate_password_reset_token",
        fake_err,
    )
    r = client.post(
        "/company/reset-password/verify",
        json={
            "business_reg_number": "x",
            "opening_date": "y",
            "ceo_name": "z",
            "email": "u@u.com",
        },
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "fail"


def test_reset_password_success(monkeypatch, client):
    """POST /company/reset-password 성공"""

    async def fake_reset(db, token, new, confirm):
        return None

    monkeypatch.setattr(
        "app.domains.company_users.router.reset_password_with_token",
        fake_reset,
    )
    r = client.post(
        "/company/reset-password",
        json={
            "reset_token": "tok",
            "new_password": "abcdefgh",
            "confirm_password": "abcdefgh",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"


@pytest.mark.parametrize("code", [400, 401, 404])
def test_reset_password_error(monkeypatch, client, code):
    """POST /company/reset-password 에러 전파"""

    async def fake_err(db, token, new, confirm):
        raise HTTPException(status_code=code, detail="err")

    monkeypatch.setattr(
        "app.domains.company_users.router.reset_password_with_token",
        fake_err,
    )
    r = client.post(
        "/company/reset-password",
        json={
            "reset_token": "tok",
            "new_password": "abcdefgh",
            "confirm_password": "abcdefgh",
        },
    )
    assert r.status_code == code
    assert r.json()["detail"] == "err"
