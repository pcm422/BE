import os

import requests
from dotenv import load_dotenv

load_dotenv()


# 사업자 등록번호 진위확인 (국세청 API)
def check_business_number_valid(b_no: str, start_dt: str, p_nm: str) -> bool:
    url = "https://api.odcloud.kr/api/nts-businessman/v1/status"
    service_key = os.getenv("SERVICE_KEY")

    if not service_key:
        raise HTTPException(
            status_code=500,
            detail={"error": "ServerError", "message": "API 키가 설정되지 않았습니다."},
        )

    headers = {"content-type": "application/json"}
    params = {"serviceKey": service_key}
    payload = {
        "businesses": [
            {
                "b_no": b_no,
                "start_dt": start_dt,  # "YYYYMMDD"
                "p_nm": p_nm,
            }
        ]
    }

    response = requests.post(url, headers=headers, params=params, json=payload)

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={"error": "ExternalAPIError", "message": "국세청 API 요청 실패"},
        )

    result = response.json().get("data", [])
    if not result:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "InvalidBusinessNumber",
                "message": "유효하지 않은 사업자등록번호입니다.",
            },
        )

    return result[0].get("valid") == "01"
    # 납세자상태(코드):
    # 01: 계속사업자,
    # 02: 휴업자,
    # 03: 폐업자
