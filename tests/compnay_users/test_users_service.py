import bcrypt
import pytest
import jwt
import time
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.domains.company_users.schemas import (
    CompanyTokenRefreshRequest,
    FindCompanyUserEmail,
    PasswordResetVerifyRequest,
)
from app.domains.company_users.service import (
    check_dupl_business_number as dup_brn,
    check_dupl_email as dup_email,
    login_company_user,
    find_company_user_email,
    refresh_company_user_access_token,
    generate_password_reset_token,
    reset_password_with_token,
)
import app.core.config as cfg
import app.domains.company_users.service as svc

# --- 더미 ORM 유저 & 결과 & 세션 정의 ---
class DummyUser:
    def __init__(self, email, raw_password=None):
        self.email = email
        if raw_password is not None:
            self.password = bcrypt.hashpw(
                raw_password.encode(), bcrypt.gensalt()
            ).decode()
        self.id = 1

class DummyResult:
    def __init__(self, v):
        self._v = v
    def scalars(self): return self
    def first(self): return self._v
    def scalar_one_or_none(self): return self._v

class DummySession:
    def __init__(self, val):
        self.val = val
    async def execute(self, query):
        return DummyResult(self.val)
    async def commit(self):
        self.committed = True
    async def refresh(self, obj):
        pass
    async def delete(self, obj):
        pass

# --- JWT 설정 픽스처 (서비스 모듈까지 덮어쓰기) ---
@pytest.fixture(autouse=True)
def jwt_settings(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    monkeypatch.setenv("ALGORITHM",  "HS256")
    # core.config 덮어쓰기
    cfg.SECRET_KEY = "testsecret"
    cfg.ALGORITHM  = "HS256"
    # service 모듈 상수도 덮어쓰기
    svc.SECRET_KEY = "testsecret"
    svc.ALGORITHM  = "HS256"


# ==== 중복 검사 테스트 ====
@pytest.mark.asyncio
async def test_check_dupl_email_conflict():
    db = DummySession(object())
    with pytest.raises(HTTPException) as exc:
        await dup_email(db, "a@b.com")
    assert exc.value.status_code == status.HTTP_409_CONFLICT

@pytest.mark.asyncio
async def test_check_dupl_email_ok():
    db = DummySession(None)
    await dup_email(db, "new@b.com")

@pytest.mark.asyncio
async def test_check_dupl_brn_conflict():
    db = DummySession(object())
    with pytest.raises(HTTPException) as exc:
        await dup_brn(db, "1234567890")
    assert exc.value.status_code == status.HTTP_409_CONFLICT

@pytest.mark.asyncio
async def test_check_dupl_brn_ok():
    db = DummySession(None)
    await dup_brn(db, "0987654321")


# ==== 로그인 테스트 ====
@pytest.mark.asyncio
async def test_login_company_user_not_found():
    db = DummySession(None)
    with pytest.raises(HTTPException) as exc:
        await login_company_user(db, "no@one.com", "pwd")
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_login_company_user_bad_password():
    dummy = DummyUser("u@u.com", raw_password="rightpw")
    db = DummySession(dummy)
    with pytest.raises(HTTPException) as exc:
        await login_company_user(db, "u@u.com", "wrongpw")
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_login_company_user_success():
    dummy = DummyUser("u@u.com", raw_password="password1")
    db = DummySession(dummy)
    user = await login_company_user(db, "u@u.com", "password1")
    assert user.email == "u@u.com"


# ==== 이메일 찾기 테스트 ====
@pytest.mark.asyncio
async def test_find_company_user_email_not_found():
    db = DummySession(None)
    payload = FindCompanyUserEmail(
        ceo_name="X", opening_date="20200101", business_reg_number="0000000000"
    )
    with pytest.raises(HTTPException) as exc:
        await find_company_user_email(db, payload)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


# ==== 토큰 재발급 테스트 ====
@pytest.mark.asyncio
async def test_refresh_company_user_access_token_not_found(monkeypatch):
    monkeypatch.setattr(
        "app.domains.company_users.service.decode_refresh_token",
        lambda t: {"sub": "no@user.com"},
    )
    db = DummySession(None)
    with pytest.raises(HTTPException) as exc:
        await refresh_company_user_access_token(
            db, CompanyTokenRefreshRequest(refresh_token="rt")
        )
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_refresh_company_user_access_token_success(monkeypatch):
    monkeypatch.setattr(
        "app.domains.company_users.service.decode_refresh_token",
        lambda t: {"sub": "ok@user.com"},
    )
    async def fake_create_access_token(data):
        return "NEWAT"
    monkeypatch.setattr(
        "app.domains.company_users.service.create_access_token",
        fake_create_access_token,
    )
    dummy = DummyUser("ok@user.com")
    db = DummySession(dummy)
    result = await refresh_company_user_access_token(
        db, CompanyTokenRefreshRequest(refresh_token="rt")
    )
    assert result["access_token"] == "NEWAT"


# ==== 비밀번호 재설정용 토큰 발급 테스트 ====
@pytest.mark.asyncio
async def test_generate_password_reset_token_success():
    user = DummyUser("a@b.com")  # raw_password 생략 가능
    db = DummySession(user)
    payload = PasswordResetVerifyRequest(
        business_reg_number="123",
        opening_date="20200101",
        ceo_name="CEO",
        email="a@b.com"
    )
    token = await generate_password_reset_token(db, payload)
    data = jwt.decode(token, "testsecret", algorithms=["HS256"])
    assert data["sub"] == "a@b.com"
    assert data["scope"] == "reset"
    assert data["exp"] > time.time()

@pytest.mark.asyncio
async def test_generate_password_reset_token_not_found():
    db = DummySession(None)
    payload = PasswordResetVerifyRequest(
        business_reg_number="xxx",
        opening_date="19000101",
        ceo_name="X",
        email="no@one.com"
    )
    with pytest.raises(HTTPException) as exc:
        await generate_password_reset_token(db, payload)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


# ==== 토큰 검증 후 비밀번호 변경 테스트 ====
@pytest.mark.asyncio
async def test_reset_password_with_token_success():
    user = DummyUser("x@y.com")
    db = DummySession(user)
    now = datetime.utcnow()
    token = jwt.encode(
        {"sub": user.email, "scope": "reset", "exp": now + timedelta(minutes=1)},
        "testsecret", algorithm="HS256"
    )
    await reset_password_with_token(db, token, "newpass12", "newpass12")
    assert getattr(db, "committed", False) is True

@pytest.mark.asyncio
async def test_reset_password_with_token_expired():
    user = DummyUser("u@u.com")
    db = DummySession(user)
    past = datetime.utcnow() - timedelta(seconds=1)
    token = jwt.encode(
        {"sub": user.email, "scope": "reset", "exp": past},
        "testsecret", algorithm="HS256"
    )
    with pytest.raises(HTTPException) as exc:
        await reset_password_with_token(db, token, "abcdefgh", "abcdefgh")
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_reset_password_with_token_invalid():
    db = DummySession(DummyUser("u@u.com"))
    with pytest.raises(HTTPException) as exc:
        await reset_password_with_token(db, "not.a.token", "abcdefgh", "abcdefgh")
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_reset_password_with_token_scope_mismatch():
    user = DummyUser("u@u.com")
    db = DummySession(user)
    token = jwt.encode(
        {"sub": user.email, "scope": "other", "exp": datetime.utcnow() + timedelta(minutes=1)},
        "testsecret", algorithm="HS256"
    )
    with pytest.raises(HTTPException) as exc:
        await reset_password_with_token(db, token, "abcdefgh", "abcdefgh")
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_reset_password_with_token_user_not_found():
    token = jwt.encode(
        {"sub": "nouser@co.com", "scope": "reset", "exp": datetime.utcnow() + timedelta(minutes=1)},
        "testsecret", algorithm="HS256"
    )
    db = DummySession(None)
    with pytest.raises(HTTPException) as exc:
        await reset_password_with_token(db, token, "abcdefgh", "abcdefgh")
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_reset_password_with_token_mismatch_passwords():
    user = DummyUser("u@u.com")
    db = DummySession(user)
    token = jwt.encode(
        {"sub": user.email, "scope": "reset", "exp": datetime.utcnow() + timedelta(minutes=1)},
        "testsecret", algorithm="HS256"
    )
    with pytest.raises(HTTPException) as exc:
        await reset_password_with_token(db, token, "abc12345", "xyz98765")
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
