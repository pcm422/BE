from typing import Any, Dict

import bcrypt
from fastapi import HTTPException, status


# 비밀번호 해싱 (DB 저장시)
def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


# 비밀번호 검증 (로그인시)
def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


# 비밀번호 일치 확인
def check_password_match(password: str, confirm_password: str) -> None:
    if confirm_password is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="비밀번호 확인이 필요합니다."
        )
    if password != confirm_password:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="비밀번호가 일치하지 않습니다."
        )


# 공통 성공 응답 형식
def success_response(message: str, data: dict = None) -> Dict[str, Any]:
    return {
        "status": "success",
        "message": message,
        "data": data,
    }


# 공통 실패 응답 형식
def error_response(
    message: str, status_code: int = status.HTTP_400_BAD_REQUEST
) -> Dict[str, Any]:
    return {
        "status": "error",
        "message": message,
        "status_code": status_code,
    }
