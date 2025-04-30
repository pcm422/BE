import json
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_resume_crud_with_exceptions(async_client: AsyncClient, user_token_and_id):
    token, user_id, _ = user_token_and_id

    # 이력서 생성
    create_payload = {
        "user_id": user_id,
        "resume_image": "",
        "desired_area": "서울",
        "introduction": "이력서 자기소개",
        "educations": [
            {
                "education_type": "고등학교",
                "school_name": "테스트고",
                "education_status": "졸업",
                "start_date": "2010-03",
                "end_date": "2013-02"
            }
        ],
        "experiences": [
            {
                "company_name": "테스트회사",
                "position": "백엔드",
                "start_date": "2015-01",
                "end_date": "2019-12",
                "description": "백엔드 개발"
            }
        ]
    }

    create_resp = await async_client.post(
        "/resumes",
        headers={"Authorization": f"Bearer {token}"},
        data={"resume_data": json.dumps(create_payload)},
        files={}
    )
    assert create_resp.status_code == 200
    created_resume = create_resp.json()["data"]
    resume_id = created_resume["id"]

    # 이력서 조회
    get_resp = await async_client.get(
        "/resumes",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["desired_area"] == "서울"

    # 이력서 수정
    update_payload = {
        "desired_area": "부산",
        "introduction": "수정된 소개",
        "educations": [],
        "experiences": []
    }

    update_resp = await async_client.patch(
        f"/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token}"},
        data={"resume_data": json.dumps(update_payload)},
        files={}
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()["data"]
    assert updated_data["desired_area"] == "부산"

    # 이력서 삭제
    delete_resp = await async_client.delete(
        f"/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["message"] == "이력서가 삭제되었습니다."

    # 삭제 후 조회 시 404
    after_delete_resp = await async_client.get(
        "/resumes",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert after_delete_resp.status_code == 404

    # 존재하지 않는 이력서 수정 시도
    wrong_update_resp = await async_client.patch(
        f"/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token}"},
        data={"resume_data": json.dumps(update_payload)},
        files={}
    )
    assert wrong_update_resp.status_code == 500 or wrong_update_resp.status_code == 404

    # 존재하지 않는 이력서 삭제 시도
    wrong_delete_resp = await async_client.delete(
        f"/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert wrong_delete_resp.status_code in(404, 500)

    # 잘못된 토큰으로 생성 요청
    bad_token_resp = await async_client.post(
        "/resumes",
        headers={"Authorization": "Bearer invalidtoken"},
        data={"resume_data": json.dumps(create_payload)},
        files={}
    )
    assert bad_token_resp.status_code == 401

    # 다른 user_id로 생성 요청
    wrong_payload = dict(create_payload)
    wrong_payload["user_id"] = 9999  # 다른 유저 ID로 조작

    user_mismatch_resp = await async_client.post(
        "/resumes",
        headers={"Authorization": f"Bearer {token}"},
        data={"resume_data": json.dumps(wrong_payload)},
        files={}
    )
    assert user_mismatch_resp.status_code == 400
    assert "사용자 ID가 일치하지 않습니다" in user_mismatch_resp.text