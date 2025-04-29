import bcrypt
import pytest
from fastapi import HTTPException, status

from app.domains.company_users.schemas import (CompanyTokenRefreshRequest,
                                               FindCompanyUserEmail)
from app.domains.company_users.service import \
    check_dupl_business_number as dup_brn
from app.domains.company_users.service import check_dupl_email as dup_email
from app.domains.company_users.service import (
    login_company_user, refresh_company_user_access_token)


# 더미 ORM 유저
class DummyUser:
    def __init__(self, email, raw_password, company=None):
        # 해시된 비밀번호 저장
        self.email = email
        self.password = bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt()).decode()
        # company_name 활용용 빈 객체
        self.company = company or type("C", (), {"company_name": "Co", "id": 1})
        self.id = 1


# 더미 결과
class DummyResult:
    def __init__(self, v):
        self._v = v

    def scalars(self):
        return self

    def first(self):
        return self._v

    def scalar_one_or_none(self):
        return self._v


# 더미 세션
class DummySession:
    def __init__(self, value):
        self.val = value

    async def execute(self, query):
        return DummyResult(self.val)

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass

    async def delete(self, obj):
        pass


@pytest.mark.asyncio
async def test_check_dupl_email_conflict():
    """이미 가입된 이메일이면 409 Conflict 예외"""
    db = DummySession(object())
    with pytest.raises(HTTPException) as exc:
        await dup_email(db, "a@b.com")
    assert exc.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_check_dupl_email_ok():
    """가입되지 않은 이메일이면 에러 없이 통과"""
    db = DummySession(None)
    # no exception
    await dup_email(db, "new@b.com")


@pytest.mark.asyncio
async def test_check_dupl_brn_conflict():
    """이미 등록된 사업자번호면 409 Conflict 예외"""
    db = DummySession(object())
    with pytest.raises(HTTPException) as exc:
        await dup_brn(db, "1234567890")
    assert exc.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_check_dupl_brn_ok():
    """미등록 사업자번호면 통과"""
    db = DummySession(None)
    await dup_brn(db, "0987654321")


@pytest.mark.asyncio
async def test_login_company_user_not_found():
    """없는 이메일로 로그인 시 404 예외"""
    db = DummySession(None)
    with pytest.raises(HTTPException) as exc:
        await login_company_user(db, "no@one.com", "pwd")
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_login_company_user_bad_password():
    """비밀번호 불일치 시 401 예외"""
    dummy = DummyUser("u@u.com", "rightpw")
    db = DummySession(dummy)
    with pytest.raises(HTTPException) as exc:
        await login_company_user(db, "u@u.com", "wrongpw")
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_login_company_user_success():
    """정상 로그인 시 User 객체 반환"""
    dummy = DummyUser("u@u.com", "password1")
    db = DummySession(dummy)
    user = await login_company_user(db, "u@u.com", "password1")
    assert user.email == "u@u.com"


@pytest.mark.asyncio
async def test_find_company_user_email_not_found():
    """일치하는 회원 없으면 404 예외"""
    from app.domains.company_users.service import find_company_user_email

    db = DummySession(None)
    payload = FindCompanyUserEmail(
        ceo_name="X", opening_date="20200101", business_reg_number="0000000000"
    )
    with pytest.raises(HTTPException) as exc:
        await find_company_user_email(db, payload)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_refresh_company_user_access_token_not_found(monkeypatch):
    # 토큰 디코딩 강제
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
    dummy = DummyUser("ok@user.com", "pw")
    db = DummySession(dummy)
    result = await refresh_company_user_access_token(
        db, CompanyTokenRefreshRequest(refresh_token="rt")
    )
    assert result["access_token"] == "NEWAT"
