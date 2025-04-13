import os

import bcrypt
import requests
from dotenv import load_dotenv

load_dotenv()


# 사업자 등록번호 진위확인 (국세청 API)
def check_business_number_valid(
    business_reg_number: str, opening_date: str, ceo_name: str
) -> bool:
    url = "https://api.odcloud.kr/api/nts-businessman/v1/status"
    service_key = os.getenv("SERVICE_KEY")

    if not service_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"API 키가 설정되지 않았습니다."},
        )

    headers = {"content-type": "application/json"}
    params = {"serviceKey": service_key}
    payload = {
        "businesses": [
            {
                "b_no": business_reg_number,
                "start_dt": opening_date,  # "YYYYMMDD"
                "p_nm": ceo_name,
            }
        ]
    }

    response = requests.post(url, headers=headers, params=params, json=payload)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"국세청 API 요청 실패"},
        )

    result = response.json().get("data", [])
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"유효하지 않은 사업자등록번호입니다."},
        )

    return result[0].get("valid") == "01"
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
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password)