import os
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.domains.users import service

load_dotenv()   # .env 파일 로드

SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")  # 기본 값 제공: "default_secret_key"
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # 기본 값: "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 엑세스 토큰 만료시간
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 리프레쉬 토큰 만료일

http_bearer = HTTPBearer()

def create_access_token(data: dict) -> str:
    to_encode = data.copy()   # 데이터 카피
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # 현재 시간 + 만료시간 계산
    to_encode.update({"exp": expire, "token_type": "access"})  # 토큰 타입 추가
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # 생성 후 반환

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()   # 데이터 카피
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)  # 현재 시간 + 만료일 계산
    to_encode.update({"exp": expire, "token_type": "refresh"})  # 토큰 타입 추가
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # 생성 후 반환

def decode_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])    # 전달받은 토큰을 디코딩
        return payload  # 페이로드 반환
    except jwt.ExpiredSignatureError:  # 만료시 에러 반환
        raise ValueError("토큰이 만료되었습니다.")
    except jwt.InvalidTokenError:  # 유효하지 않은 토큰일 경우 에러 반환
        raise ValueError("유효하지 않은 토큰입니다.")

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # 토큰 디코딩하여 페이로드 추출
        user_id: int = payload.get("sub")  # sub값 가져옴 -> 사용자 아이디
        if user_id is None:  # 유저 아이디 없으면 에러 반환
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 인증 토큰입니다.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return user_id  # 검증된 사용자 반환
    except jwt.ExpiredSignatureError:   # 토큰 만료시 에러 반환
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.JWTError:    # 기타 토큰 관련오류시 에러 반환
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰 오류입니다.",
            headers={"WWW-Authenticate": "Bearer"}
        )

async def get_current_user(
    db: AsyncSession = Depends(get_db_session),   # DB 세션
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
):
    token = credentials.credentials  # Bearer 토큰 부분 추출
    payload = decode_jwt_token(token)  # 페이로드 토큰 디코딩해 받음
    sub = payload.get("sub")   # sub 값을 가져옴
    if not sub:   # sub값 없으면 에러
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰(sub 누락)")
    user = await service.get_user_by_id(db, int(sub))
    if not user:  # 사용자 없으면 에러
        raise HTTPException(status_code=404, detail="존재하지 않는 사용자")
    return user  # 유저 반환