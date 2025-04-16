import os

import bcrypt
import httpx
from dotenv import load_dotenv
from fastapi import HTTPException, status

load_dotenv()


# 사업자 등록번호 진위확인 (국세청 API)
async def check_business_number_valid(
    business_reg_number: str, opening_date: str, ceo_name: str
) -> bool:
    service_key = os.getenv("BRN_API_KEY")
    url = "https://api.odcloud.kr/api/nts-businessman/v1/validate"
    params = {"serviceKey": service_key}

    if not service_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API 키가 설정되지 않았습니다.",
        )

    headers = {"Content-type": "application/json"}
    payload = {
        "businesses": [
            {
                "b_no": business_reg_number.replace("-", ""),
                "start_dt": opening_date.replace("-", ""),
                "p_nm": ceo_name,
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, params=params, json=payload)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"국세청 API 요청 실패: {response.text}",
        )

    data = response.json().get("data", [])
    if not data or not isinstance(data, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="국세청 응답에 데이터가 없습니다.",
        )

    status_code = data[0].get("valid")  # '01', '02', '03' 중 하나

    if status_code == "01":
        return True
    elif status_code == "02":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="휴업 중인 사업자입니다."
        )
    elif status_code == "03":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="폐업된 사업자입니다."
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 사업자등록번호입니다.",
        )

    # 납세자상태(코드):
    # 01: 계속사업자,
    # 02: 휴업자,
    # 03: 폐업자


# 비밀번호 해싱 (DB 저장시)
def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


# 비밀번호 검증 (로그인시)
def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


# 비밀번호 일치 확인
def check_password_match(password: str, confirm_password: str) -> bool:
    if confirm_password is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="비밀번호 확인이 필요합니다."
        )
    if password != confirm_password:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="비밀번호가 일치하지 않습니다."
        )


# 성공 응답 함수
def success_response(message: str, data: dict = None, status_code: int = 200):
    return {
        "status": "success",
        "message": message,
        "data": data,
    }


# 실패 응답 함수
def error_response(message: str, status_code: int = 400):
    return {
        "status": "error",
        "message": message,
        "status_code": status_code,
    }
