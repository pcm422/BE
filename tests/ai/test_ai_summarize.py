import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any

from app.main import app

client = TestClient(app)

# 유효한 테스트 데이터
valid_job_data: Dict[str, Any] = {
    "title": "세일즈 영업직 채용",
    "job_category": "영업·상담",
    "education": "고졸 이상",
    "employment_type": "정규직",
    "payment_method": "연봉",
    "salary": 37450000,
    "work_duration": "1년 이상",
    "is_work_duration_negotiable": False,
    "work_days": "월~금",
    "is_work_days_negotiable": True,
    "work_start_time": "09:00",
    "work_end_time": "18:00",
    "is_work_time_negotiable": False,
    "career": "경력",
    "work_place_name": "토스인슈어런스",
    "work_address": "인천광역시 중구",
    "benefits": "4대보험, 중식 제공",
    "preferred_conditions": "유사업무 경력자",
    "description": "고객과의 커뮤니케이션 능력이 뛰어난 인재를 찾습니다."
}

# 필수 필드 누락 (title 없음)
missing_required_field = {k: v for k, v in valid_job_data.items() if k != "title"}

# salary 음수 (논리적 비정상)
negative_salary_data = valid_job_data.copy()
negative_salary_data["salary"] = -5000000


@pytest.mark.parametrize(
    "payload, expected_status",
    [
        (valid_job_data, 200),
        (missing_required_field, 422),
        (negative_salary_data, 200),  # 구조상 통과하나 의미상 테스트
    ]
)
def test_ai_summarize_input_variants(payload, expected_status):
    response = client.post("/ai/summarize", json=payload)
    assert response.status_code == expected_status

    if expected_status == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "summary" in data["data"]
        assert isinstance(data["data"]["summary"], str)
        assert len(data["data"]["summary"]) > 0


def test_ai_summarize_output_format():
    """요약문이 '회사이름에서~'로 시작하고 마침표로 끝나는지 확인"""
    response = client.post("/ai/summarize", json=valid_job_data)
    assert response.status_code == 200

    summary = response.json()["data"]["summary"]
    assert "에서" in summary[:15]
    assert summary.strip().endswith(".")
    for ch in ["[", "]", "/", "\"", "'"]:
        assert ch not in summary

# 사용자가 직접 입력하는 구조가 아닌,
# 저장된 공고 데이터를 기반으로 가져오는거라 생략함
# 필수 필드만 있을 때도 동작 하는지 확인 ->불필요
# def test_ai_summarize_minimum_required_fields():
#     minimal_data = {
#         "title": "알바생 모집",
#         "job_category": "서비스직",
#         "education": "무관",
#         "employment_type": "계약직",
#         "payment_method": "시급",
#         "salary": 10000,
#         "is_work_duration_negotiable": False,
#         "is_work_days_negotiable": False,
#         "is_work_time_negotiable": False,
#         "career": "무관",
#         "work_place_name": "GS25",
#         "work_address": "서울시 마포구"
#     }
#     response = client.post("/ai/summarize", json=minimal_data)
#     assert response.status_code == 200
#     assert "summary" in response.json()["data"]

from unittest.mock import patch,AsyncMock

@patch("app.domains.ai.service.call_clova_summary", new_callable=AsyncMock)
def test_ai_summarize_clova_empty_response(mock_clova):
    mock_clova.return_value = ""

    response = client.post("/ai/summarize", json=valid_job_data)

    print("🔥 Mock was called:", mock_clova.called)  # ← mock 작동 확인용
    print("🔥 Mock returned:", mock_clova.return_value)
    print("🔥 Response JSON:", response.json())

    assert response.status_code == 502
    assert "요약 결과가 비어 있습니다" in response.json()["detail"]
