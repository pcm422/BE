import os
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.domains.users.service import (  # UserRegister 스키마 임포트
    create_access_token, create_refresh_token, get_user_by_email)
from app.models.users import EmailVerification

router = APIRouter(prefix="/auth", tags=["Oauth2"])

# 카카오 로그인
@router.get("/kakao/login", response_model=dict)
async def auth_kakao_login(
    code: str = Query(...),  # 프론트엔드에서 전달받은 카카오 인가 코드 (쿼리 파라미터)
    db: AsyncSession = Depends(get_db_session),  # DB 세션 의존성 주입
):
    """
    카카오 로그인 엔드포인트.
    프론트엔드에서 인가 코드를 포함한 요청을 보내면,
    카카오 서버에 토큰 요청 후 사용자 정보를 획득하고,
    내부 DB에서 사용자 존재 여부를 확인(또는 신규가입)한 후 JWT 토큰을 발급합니다.
    """
    # 카카오 토큰 교환 URL, 클라이언트 ID, 시크릿, 리다이렉트 URI는 환경변수에서 가져옵니다.
    token_url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": os.getenv("KAKAO_CLIENT_ID"),
        "client_secret": os.getenv(
            "KAKAO_SECRET"
        ),  # KAKAO_SECRET 키 사용 (환경변수 이름에 따라 수정)
        "redirect_uri": os.getenv(
            "KAKAO_REDIRECT_URI", "http://localhost:5173/auth/kakao/login"
        ),
        "code": code,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=data, headers=headers)
        token_json = token_response.json()
        # 응답 JSON을 로그에 출력해서 오류 원인을 확인합니다.
        print("Kakao token response:", token_json)
        access_token = token_json.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=400, detail="카카오 토큰 발급에 실패하였습니다."
            )

        # 사용자 정보 요청 URL 및 헤더 설정
        user_info_url = "https://kapi.kakao.com/v2/user/me"
        profile_headers = {"Authorization": f"Bearer {access_token}"}
        # 카카오에서 사용자 정보 요청 (POST 방식, 카카오 API는 POST를 사용하는 경우가 있음)
        user_response = await client.post(user_info_url, headers=profile_headers)
        user_info = user_response.json()

    # 카카오 계정 정보에서 이메일과 닉네임 추출
    kakao_account = user_info.get("kakao_account", {})
    email = kakao_account.get("email")
    nickname = kakao_account.get("profile", {}).get("nickname", "Kakao User")

    if not email:
        raise HTTPException(
            status_code=400, detail="카카오 계정에 이메일 정보가 없습니다."
        )

    user_result = await get_user_by_email(db, email)
    user = user_result if not isinstance(user_result, dict) else None

    # 사용자가 없으면 추가 정보 입력이 필요한 단계로 넘김
    if not user:
        # 기존 인증 데이터 확인
        result = await db.execute(
            select(EmailVerification)
            .where(EmailVerification.email == email)
            .order_by(EmailVerification.id.desc())  # 가장 최근 레코드 우선
            .limit(1)
        )
        verification = result.scalar_one_or_none()

        if not verification:
            # 없다면 새로 생성
            verification = EmailVerification(
                email=email,
                token=access_token,  # 임시로 access_token 저장
                is_verified=True,
                expires_at=datetime.now(),  # 만료 시간은 현재 시간으로 설정
                user_type="user",  # 또는 "company"로 설정할 수 있음
            )
            db.add(verification)
        else:
            # 있다면 상태 업데이트
            verification.is_verified = True
            verification.token = access_token
            verification.expires_at = datetime.now()

        await db.commit()

        return {
            "status": "need_register",
            "message": "카카오 계정으로 로그인은 성공했지만 추가 정보 입력이 필요합니다.",
            "data": {
                "email": email,
                "name": nickname,
                "social_type": "kakao"
            },
        }

    # is_active 활성화
    if not user.is_active:
        user.is_active = True
        await db.commit()

    # JWT 토큰 발급
    access_jwt = await create_access_token({"sub": str(user.id)})
    refresh_jwt = await create_refresh_token({"sub": str(user.id)})

    return {
        "status": "success",
        "message": "카카오 로그인에 성공하였습니다.",
        "data": {
            "access_token": access_jwt,
            "refresh_token": refresh_jwt,
            "user": {"id": user.id, "name": user.name, "email": user.email},
        },
    }


# 네이버 로그인 (리다이렉트와 콜백을 합친 엔드포인트)
@router.get("/naver/login", response_model=dict)
async def auth_naver_login(
    code: str = Query(...),  # 프론트엔드에서 전달받은 네이버 인가 코드
    state: str = Query(...),  # 네이버는 state 값도 전달됩니다.
    db: AsyncSession = Depends(get_db_session),  # DB 세션 의존성 주입
):
    """
    네이버 로그인 엔드포인트.
    프론트엔드에서 인가 코드와 state를 포함한 요청을 보내면,
    네이버 서버에 토큰 요청 후 사용자 정보를 획득하고,
    내부 DB에서 사용자 존재 여부를 확인(또는 신규가입)한 후 JWT 토큰을 발급합니다.
    """
    if not state or state.lower() == "null":
        state = "null"

    token_url = "https://nid.naver.com/oauth2.0/token"
    params = {
        "grant_type": "authorization_code",
        "client_id": os.getenv("NAVER_CLIENT_ID"),
        "client_secret": os.getenv("NAVER_CLIENT_SECRET"),
        "code": code,
        "state": state,
    }

    async with httpx.AsyncClient() as client:
        # 네이버에 액세스 토큰 요청
        token_response = await client.post(token_url, params=params)
        token_json = token_response.json()
        access_token = token_json.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=400, detail="네이버 토큰 발급에 실패하였습니다."
            )

        # 네이버 사용자 정보 요청
        user_info_url = "https://openapi.naver.com/v1/nid/me"
        headers = {"Authorization": f"Bearer {access_token}"}
        user_response = await client.post(user_info_url, headers=headers)
        user_info = user_response.json().get("response", {})

    email = user_info.get("email")
    nickname = user_info.get("name", "Naver User")

    if not email:
        raise HTTPException(
            status_code=400, detail="네이버 계정에 이메일 정보가 없습니다."
        )

    user_result = await get_user_by_email(db, email)
    user = user_result if not isinstance(user_result, dict) else None

    if not user:

        # 기존 인증 데이터 확인
        result = await db.execute(
            select(EmailVerification).where(EmailVerification.email == email)
        )
        verification = result.scalar_one_or_none()

        if not verification:
            # 없다면 새로 생성
            verification = EmailVerification(
                email=email,
                token=access_token,  # 임시로 access_token 저장
                is_verified=True,
                expires_at=datetime.now(),  # 만료 시간은 현재 시간으로 설정
                user_type="user",  # 또는 "company"로 설정할 수 있음
            )
            db.add(verification)
        else:
            # 있다면 상태 업데이트
            verification.is_verified = True
            verification.token = access_token
            verification.expires_at = datetime.now()

        await db.commit()

        return {
            "status": "need_register",
            "message": "네이버 계정으로 로그인은 성공했지만 추가 정보 입력이 필요합니다.",
            "data": {
                "email": email,
                "name": nickname,
                "social_type": "naver"
            },
        }

    # is_active 활성화
    if not user.is_active:
        user.is_active = True
        await db.commit()

    # JWT 토큰 발급
    access_jwt = await create_access_token({"sub": str(user.id)})
    refresh_jwt = await create_refresh_token({"sub": str(user.id)})

    return {
        "status": "success",
        "message": "네이버 로그인에 성공하였습니다.",
        "data": {
            "access_token": access_jwt,
            "refresh_token": refresh_jwt,
            "user": {"id": user.id, "name": user.name, "email": user.email},
        },
    }
