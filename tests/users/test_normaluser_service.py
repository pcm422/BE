import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import User


@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient):
    payload = {
        "name": "홍길동",
        "email": "hong@example.com",
        "password": "password123",
        "phone_number": "010-1234-5678",
        "birthday": "1990-01-01",
        "gender": "남성",
        "signup_purpose": "취업",
        "referral_source": "구글 검색",
        "interests": ["운전·배달", "전문-생산직"]
    }
    response = await async_client.post("/user/register", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_login_user(async_client: AsyncClient, db_session: AsyncSession):
    await async_client.post("/user/register", json={
        "name": "홍길동",
        "email": "hong@example.com",
        "password": "password123",
    })

    # 이메일 인증 없이 로그인 시도를 위해 is_active를 True로 설정
    result = await db_session.execute(select(User).where(User.email == "hong@example.com"))
    user = result.scalar_one()
    user.is_active = True
    await db_session.commit()

    response = await async_client.post("/user/login", json={
        "email": "hong@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "accesstoken" in response.json()["data"]


@pytest.mark.asyncio
async def test_get_me(async_client: AsyncClient, user_token_and_id):
    token, _, _ = user_token_and_id
    response = await async_client.get(
        "/user/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"]


@pytest.mark.asyncio
async def test_update_profile(async_client: AsyncClient, user_token_and_id):
    token, user_id, _ = user_token_and_id
    payload = {
        "name": "홍수정",
        "phone_number": "010-5678-1234"
    }
    response = await async_client.patch(
        f"/user/{user_id}", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "홍수정"


@pytest.mark.asyncio
async def test_recommend_jobs(async_client: AsyncClient, user_token_and_id):
    token, _, _ = user_token_and_id
    response = await async_client.get(
        "/user/recommend", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code in [200, 404]  # 관심공고 없으면 404 가능


@pytest.mark.asyncio
async def test_check_email(async_client: AsyncClient):
    response = await async_client.get("/check-email", params={"email": "hong@example.com"})
    assert response.status_code == 200
    assert "is_duplicate" in response.json()


@pytest.mark.asyncio
async def test_password_reset_verify(async_client: AsyncClient):
    await async_client.post("/user/register", json={
        "name": "홍길동",
        "email": "hong@example.com",
        "password": "password123",
        "phone_number": "010-1234-5678",
        "birthday": "1990-01-01"
    })

    payload = {
        "email": "hong@example.com",
        "name": "홍길동",
        "phone_number": "010-1234-5678",
        "birthday": "1990-01-01"
    }
    response = await async_client.post("/user/password/verify", json=payload)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_password_reset_confirm(async_client: AsyncClient):
    # Register user to ensure existence
    await async_client.post("/user/register", json={
        "name": "홍길동",
        "email": "hong@example.com",
        "password": "password123",
        "phone_number": "010-1234-5678",
        "birthday": "1990-01-01"
    })

    verify_response = await async_client.post("/user/password/verify", json={
        "email": "hong@example.com",
        "name": "홍길동",
        "phone_number": "010-1234-5678",
        "birthday": "1990-01-01"
    })
    if verify_response.status_code != 200:
        pytest.fail(f"비밀번호 검증 실패: {verify_response.json()}")

    user_id = verify_response.json()["data"]["user_id"]
    payload = {
        "user_id": user_id,
        "new_password": "newpass123",
        "confirm_password": "newpass123"
    }

    response = await async_client.post("/user/password/reset", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "비밀번호가 재설정되었습니다."


@pytest.mark.asyncio
async def test_find_email(async_client: AsyncClient):
    await async_client.post("/user/register", json={
        "name": "홍길동",
        "email": "hong@example.com",
        "password": "password123",
        "phone_number": "010-1234-5678",
        "birthday": "1990-01-01"
    })

    payload = {
        "name": "홍길동",
        "phone_number": "010-1234-5678",
        "birthday": "1990-01-01"
    }
    response = await async_client.post("/user/find_email", json=payload)
    assert response.status_code == 200
    assert "email" in response.json()["data"]


@pytest.mark.asyncio
async def test_delete_user(async_client: AsyncClient, user_token_and_id):
    token, user_id, _ = user_token_and_id
    response = await async_client.delete(
        f"/user/{user_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "회원탈퇴가 정상적으로 처리되었습니다."
