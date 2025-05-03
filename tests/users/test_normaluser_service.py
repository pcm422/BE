import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from datetime import datetime, timedelta, timezone

from app.models import User
from app.models.users import EmailVerification


class TestUserEndpoints:

    @pytest.mark.asyncio
    async def test_register_user(self, async_client: AsyncClient, db_session: AsyncSession):
        # 이메일 인증 정보 DB에 삽입 (인증 완료 상태)
        await db_session.execute(
            insert(EmailVerification).values(
                email="hong@example.com",
                token="dummy-token",
                is_verified=True,
                user_type="user",
                expires_at=datetime.now() + timedelta(minutes=30)
            )
        )
        await db_session.commit()  # DB 변경사항 커밋

        # 회원가입 요청에 사용할 페이로드 정의
        payload = {
            "name": "홍길동",  # 사용자 이름
            "email": "hong@example.com",  # 이메일
            "password": "password123",  # 비밀번호
            "phone_number": "010-1234-5678",  # 전화번호
            "birthday": "1990-01-01",  # 생년월일
            "gender": "남성",  # 성별
            "signup_purpose": "취업",  # 가입 목적
            "referral_source": "구글 검색",  # 유입 경로
            "interests": ["운전·배달", "전문-생산직"]  # 관심 분야
        }
        response = await async_client.post("/user/register", json=payload)  # 회원가입 요청 전송
        assert response.status_code == 200  # 정상 등록 응답 확인
        assert response.json()["status"] == "success"  # 성공 상태 메시지 확인


    @pytest.mark.asyncio
    async def test_login_user(self, async_client: AsyncClient, db_session: AsyncSession):
        # 이메일 인증 정보 DB에 삽입 (인증 완료 상태)
        await db_session.execute(
            insert(EmailVerification).values(
                email="hong@example.com",
                token="dummy-token",
                is_verified=True,
                user_type="user",
                expires_at=datetime.now() + timedelta(minutes=30)
            )
        )
        await db_session.commit()  # DB 변경사항 커밋

        # 회원가입 요청 전송 (로그인 테스트를 위한 사용자 생성)
        await async_client.post("/user/register", json={
            "name": "홍길동",  # 사용자 이름
            "email": "hong@example.com",  # 이메일
            "password": "password123",  # 비밀번호
            "phone_number": "010-1234-5678",  # 전화번호
            "birthday": "1990-01-01",  # 생년월일
        })

        # DB에서 해당 이메일 사용자 조회
        result = await db_session.execute(select(User).where(User.email == "hong@example.com"))
        user = result.scalar_one()
        user.is_active = True  # 사용자 활성화 처리 (이메일 인증 완료 상태로 변경)
        await db_session.commit()  # 변경사항 커밋

        # 로그인 요청 전송
        response = await async_client.post("/user/login", json={
            "email": "hong@example.com",  # 이메일
            "password": "password123"  # 비밀번호
        })
        assert response.status_code == 200  # 로그인 성공 응답 확인
        assert "accesstoken" in response.json()["data"]  # 액세스 토큰 포함 여부 확인


    @pytest.mark.asyncio
    async def test_login_user_expired_token(self, async_client: AsyncClient, db_session: AsyncSession):
        # 만료된 이메일 인증 토큰 생성 (현재 시간보다 1분 이전)
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db_session.execute(
            insert(EmailVerification).values(
                email="expired@example.com",
                token="expired-token",
                is_verified=True,
                user_type="user",
                expires_at=expired_time
            )
        )
        await db_session.commit()  # DB 변경사항 커밋

        # 만료된 토큰으로 로그인 시도
        response = await async_client.post("/user/login", json={
            "email": "expired@example.com",  # 이메일
            "password": "password123"  # 비밀번호
        })
        assert response.status_code == 401  # 인증 실패(토큰 만료) 상태코드 확인

    @pytest.mark.asyncio
    async def test_login_user_invalid_token_format(self, async_client: AsyncClient):
        # 잘못된 형식의 JWT 토큰을 가진 Authorization 헤더로 사용자 정보 조회 요청
        response = await async_client.get(
            "/user/me", headers={"Authorization": "Bearer not.a.jwt"}
        )
        assert response.status_code == 401  # 인증 실패 상태코드 확인

    @pytest.mark.asyncio
    async def test_get_me_without_token(self, async_client: AsyncClient):
        # 인증 토큰 없이 사용자 정보 조회 요청
        response = await async_client.get("/user/me")
        assert response.status_code == 422  # 인증 실패 상태코드 확인

    @pytest.mark.asyncio
    async def test_password_reset_confirm_wrong_token(self, async_client: AsyncClient):
        # 존재하지 않는 사용자 ID로 비밀번호 재설정 요청 페이로드 정의
        payload = {
            "user_id": 999999,  # 존재하지 않는 ID
            "new_password": "newpass123",  # 새 비밀번호
            "confirm_password": "newpass123"  # 비밀번호 확인
        }
        # 비밀번호 재설정 요청 전송
        response = await async_client.post("/user/password/reset", json=payload)
        assert response.status_code in [400, 404]  # 잘못된 요청 또는 사용자 없음 응답 확인

    @pytest.mark.asyncio
    async def test_password_reset_confirm_mismatched_passwords(self, async_client: AsyncClient, db_session: AsyncSession):
        # 이메일 인증 정보 DB에 삽입 (인증 완료 상태)
        await db_session.execute(
            insert(EmailVerification).values(
                email="mismatch@example.com",
                token="dummy-token",
                is_verified=True,
                user_type="user",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=30)
            )
        )
        await db_session.commit()  # DB 변경사항 커밋

        # 회원가입 요청 전송
        register_resp = await async_client.post("/user/register", json={
            "name": "홍길동",  # 사용자 이름
            "email": "mismatch@example.com",  # 이메일
            "password": "password123",  # 비밀번호
            "phone_number": "010-1234-5678",  # 전화번호
            "birthday": "1990-01-01"  # 생년월일
        })

        # 비밀번호 재설정 전 검증 요청 전송
        verify_resp = await async_client.post("/user/password/verify", json={
            "email": "mismatch@example.com",  # 이메일
            "name": "홍길동",  # 이름
            "phone_number": "010-1234-5678",  # 전화번호
            "birthday": "1990-01-01"  # 생년월일
        })
        if verify_resp.status_code != 200:
            pytest.fail("비밀번호 검증 실패")  # 검증 실패 시 테스트 중단

        user_id = verify_resp.json()["data"]["user_id"]  # 사용자 ID 추출

        # 비밀번호와 확인 비밀번호가 일치하지 않는 페이로드 정의
        payload = {
            "user_id": user_id,  # 사용자 ID
            "new_password": "newpass123",  # 새 비밀번호
            "confirm_password": "differentpass"  # 확인 비밀번호 (불일치)
        }
        # 비밀번호 재설정 요청 전송
        response = await async_client.post("/user/password/reset", json=payload)
        assert response.status_code == 400  # 비밀번호 불일치로 인한 실패 상태코드 확인


    @pytest.mark.asyncio
    async def test_get_me(self, async_client: AsyncClient, user_token_and_id):
        token, _, _ = user_token_and_id  # 액세스 토큰 및 사용자 정보 추출
        # 인증 헤더를 포함하여 사용자 정보 조회 요청
        response = await async_client.get(
            "/user/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200  # 성공 상태코드 확인
        assert response.json()["email"]  # 이메일 정보 존재 여부 확인


    @pytest.mark.asyncio
    async def test_update_profile(self, async_client: AsyncClient, user_token_and_id):
        token, user_id, _ = user_token_and_id  # 토큰 및 사용자 ID 추출
        # 프로필 업데이트 요청 페이로드 정의
        payload = {
            "name": "홍수정",  # 변경할 이름
            "phone_number": "010-5678-1234"  # 변경할 전화번호
        }
        # 인증 헤더 포함하여 사용자 프로필 수정 요청 전송
        response = await async_client.patch(
            f"/user/{user_id}", json=payload, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200  # 성공 상태코드 확인
        assert response.json()["data"]["name"] == "홍수정"  # 이름 변경 반영 여부 확인


    @pytest.mark.asyncio
    async def test_recommend_jobs(self, async_client: AsyncClient, user_token_and_id):
        token, _, _ = user_token_and_id  # 액세스 토큰 추출
        # 관심 공고 추천 요청 (인증 헤더 포함)
        response = await async_client.get(
            "/user/recommend", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in [200, 404]  # 관심공고 없으면 404 가능, 성공도 가능


    @pytest.mark.asyncio
    async def test_password_reset_verify(self, async_client: AsyncClient, db_session: AsyncSession):
        # 이메일 인증 정보 DB에 삽입 (인증 완료 상태)
        await db_session.execute(
            insert(EmailVerification).values(
                email="hong@example.com",
                token="dummy-token",
                is_verified=True,
                user_type="user",
                expires_at=datetime.now() + timedelta(minutes=30)
            )
        )
        await db_session.commit()  # DB 변경사항 커밋

        # 회원가입 요청 전송
        await async_client.post("/user/register", json={
            "name": "홍길동",  # 사용자 이름
            "email": "hong@example.com",  # 이메일
            "password": "password123",  # 비밀번호
            "phone_number": "010-1234-5678",  # 전화번호
            "birthday": "1990-01-01"  # 생년월일
        })

        # 비밀번호 재설정 검증 요청 페이로드 정의
        payload = {
            "email": "hong@example.com",  # 이메일
            "name": "홍길동",  # 이름
            "phone_number": "010-1234-5678",  # 전화번호
            "birthday": "1990-01-01"  # 생년월일
        }
        response = await async_client.post("/user/password/verify", json=payload)  # 검증 요청 전송
        assert response.status_code == 200  # 성공 상태코드 확인

    @pytest.mark.asyncio
    async def test_password_reset_confirm(self, async_client: AsyncClient, db_session: AsyncSession):
        # 이메일 인증 정보 DB에 삽입 (인증 완료 상태)
        await db_session.execute(
            insert(EmailVerification).values(
                email="hong@example.com",
                token="dummy-token",
                is_verified=True,
                user_type="user",
                expires_at=datetime.now() + timedelta(minutes=30)
            )
        )
        await db_session.commit()  # DB 변경사항 커밋

        # 회원가입 요청 전송
        await async_client.post("/user/register", json={
            "name": "홍길동",  # 사용자 이름
            "email": "hong@example.com",  # 이메일
            "password": "password123",  # 비밀번호
            "phone_number": "010-1234-5678",  # 전화번호
            "birthday": "1990-01-01"  # 생년월일
        })

        # 비밀번호 재설정 검증 요청 전송
        verify_response = await async_client.post("/user/password/verify", json={
            "email": "hong@example.com",  # 이메일
            "name": "홍길동",  # 이름
            "phone_number": "010-1234-5678",  # 전화번호
            "birthday": "1990-01-01"  # 생년월일
        })
        if verify_response.status_code != 200:
            pytest.fail(f"비밀번호 검증 실패: {verify_response.json()}")  # 실패 시 테스트 중단

        user_id = verify_response.json()["data"]["user_id"]  # 사용자 ID 추출

        # 비밀번호 재설정 요청 페이로드 정의
        payload = {
            "user_id": user_id,  # 사용자 ID
            "new_password": "newpass123",  # 새 비밀번호
            "confirm_password": "newpass123"  # 확인 비밀번호
        }

        # 비밀번호 재설정 요청 전송
        response = await async_client.post("/user/password/reset", json=payload)
        assert response.status_code == 200  # 성공 상태코드 확인
        assert response.json()["message"] == "비밀번호가 재설정되었습니다."  # 성공 메시지 확인


    @pytest.mark.asyncio
    async def test_find_email(self, async_client: AsyncClient, db_session: AsyncSession):
        # 이메일 인증 정보 DB에 삽입 (인증 완료 상태)
        await db_session.execute(
            insert(EmailVerification).values(
                email="hong@example.com",
                token="dummy-token",
                is_verified=True,
                user_type="user",
                expires_at=datetime.now() + timedelta(minutes=30)
            )
        )
        await db_session.commit()  # DB 변경사항 커밋

        # 회원가입 요청 전송
        await async_client.post("/user/register", json={
            "name": "홍길동",  # 사용자 이름
            "email": "hong@example.com",  # 이메일
            "password": "password123",  # 비밀번호
            "phone_number": "010-1234-5678",  # 전화번호
            "birthday": "1990-01-01"  # 생년월일
        })

        # 이메일 찾기 요청 페이로드 정의
        payload = {
            "name": "홍길동",  # 이름
            "phone_number": "010-1234-5678",  # 전화번호
            "birthday": "1990-01-01"  # 생년월일
        }
        response = await async_client.post("/user/find_email", json=payload)  # 이메일 찾기 요청 전송
        assert response.status_code == 200  # 성공 상태코드 확인
        assert "email" in response.json()["data"]  # 이메일 정보 포함 여부 확인


    @pytest.mark.asyncio
    async def test_delete_user(self, async_client: AsyncClient, user_token_and_id):
        token, user_id, _ = user_token_and_id  # 토큰 및 사용자 ID 추출
        # 인증 헤더 포함하여 사용자 삭제 요청 전송
        response = await async_client.delete(
            f"/user/{user_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200  # 성공 상태코드 확인
        assert response.json()["message"] == "회원탈퇴가 정상적으로 처리되었습니다."  # 성공 메시지 확인
