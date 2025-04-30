from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app  # FastAPI 앱 임포트
from app.core.db import get_db_session  # DB 세션 의존성
from app.models import User, Resume, JobPosting, CompanyUser, CompanyInfo  # 테스트에 필요한 모델 임포트
from app.core.utils import create_access_token  # JWT 토큰 생성 유틸
from app.models.job_postings import EducationEnum, PaymentMethodEnum, JobCategoryEnum, WorkDurationEnum


# --- 테스트를 위한 DB 세션 오버라이드 설정 ---
@pytest.fixture(autouse=True)
def override_db_session(db_session: AsyncSession):
    """
    모든 요청에 대해 테스트용 세션을 사용하도록 의존성 오버라이드
    """
    app.dependency_overrides[get_db_session] = lambda: db_session
    yield
    app.dependency_overrides.clear()


# --- 사용자 및 인증 토큰 생성 피처 ---
@pytest.fixture()
async def user_token_and_id(db_session: AsyncSession):
    """
    테스트용 일반 사용자와 JWT 토큰 생성
    """
    user = User(
        name="테스트유저",
        email="testuser@example.com",
        password="securepwd",
        gender="남성",
        phone_number="010-0000-0000",
        birthday="1990-01-01",
        signup_purpose="테스트",
        referral_source="검색"
    )  # User 객체 생성
    db_session.add(user)  # 세션에 추가
    await db_session.commit()  # 변경사항 커밋
    await db_session.refresh(user)  # 객체 리프레시

    access_token = await create_access_token(data={"sub": str(user.id)})
    return access_token, user.id


# --- 테스트를 위한 기본 데이터 설정 ---
@pytest.fixture()
async def base_data(db_session: AsyncSession, user_token_and_id):
    """
    기본 이력서, 채용공고, 기업 정보 생성
    """
    _, user_id = user_token_and_id
    # 이력서 생성: 사용자 ID만 설정
    resume = Resume(user_id=user_id)
    db_session.add(resume)
    await db_session.commit()       # 커밋하여 resume.id 확보
    await db_session.refresh(resume)  # 리프레시
    # CompanyInfo 및 CompanyUser 생성 (회원가입 요청 시점처럼 한 번에 처리)
    company = CompanyInfo(
        company_name="오즈코딩스쿨",
        ceo_name="홍길동",
        business_reg_number="4561234860",
        opening_date="2020-01-01",
        company_intro="개발자 양성을 목표로 하는 기업입니다.",
        manager_name="김담당",
        manager_phone="01012345678",
        manager_email="ghaj4512@naver.com"
    )
    db_session.add(company)
    await db_session.flush()  # company.id 확보

    comp_user = CompanyUser(
        email="test1@example.com",
        password="qwe123!@#",
        company_id=company.id
    )
    db_session.add(comp_user)
    await db_session.flush()
    await db_session.commit()
    await db_session.refresh(comp_user)
    comp_user_token = await create_access_token(data={"sub": str(comp_user.email)})

    # JobPosting 생성
    posting = JobPosting(
        title="테스트공고",
        company_id=company.id,
        author_id=comp_user.id,
        recruit_period_start=date(2025, 5, 1),
        recruit_period_end=date(2025, 6, 1),
        is_always_recruiting=False,
        education=EducationEnum.college_4,
        recruit_number=1,
        payment_method=PaymentMethodEnum.monthly,
        job_category=JobCategoryEnum.it,
        work_duration=WorkDurationEnum.more_6_months,
        is_work_duration_negotiable=False,
        career="무관",
        employment_type="정규직",
        salary=3000,
        work_days="월~금",
        is_work_days_negotiable=False,
        is_schedule_based=False,
        work_address="서울시 강남구",
        work_place_name="본사",
        is_work_time_negotiable=False,
        postings_image="https://example.com/default.png",
    )
    db_session.add(posting)
    await db_session.commit()  # 커밋
    await db_session.refresh(resume)
    await db_session.refresh(posting)
    return resume, posting, comp_user, comp_user_token


# --- API 전체 기능 테스트 ---
@pytest.mark.asyncio
async def test_full_application_flow(async_client: AsyncClient, user_token_and_id, base_data):
    """
    사용자의 지원 생성, 조회, 취소 및 기업 조회/상태 변경 흐름 테스트
    """
    access_token, user_id = user_token_and_id  # 토큰과 사용자 ID 언패킹
    resume, posting, comp_user, comp_user_token = base_data  # 기본 데이터 언패킹

    # 1) 지원 생성
    create_resp = await async_client.post(
        "/applications",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"job_posting_id": posting.id},
    )  # POST /applications 요청
    assert create_resp.status_code == 201  # 생성 성공 검증
    data = create_resp.json()  # 응답 JSON 파싱
    assert data["user_id"] == user_id  # user_id 확인
    app_id = data["id"]  # 생성된 지원 ID 저장

    # 2) 내 지원 조회
    list_resp = await async_client.get(
        "/applications",
        headers={"Authorization": f"Bearer {access_token}"},
    )  # GET /applications 요청
    assert list_resp.status_code == 200  # 조회 성공
    list_data = list_resp.json()
    assert any(item["id"] == app_id for item in list_data)  # 생성된 지원 포함 여부

    # 3) 특정 공고의 내 지원 상세 조회
    detail_resp = await async_client.get(
        f"/applications/posting/{posting.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )  # GET /applications/posting/{id}
    assert detail_resp.status_code == 200  # 상세 조회 성공

    # 4) 지원 취소
    del_resp = await async_client.delete(
        f"/applications/{app_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )  # DELETE /applications/{id}
    assert del_resp.status_code == 200  # 삭제 성공

    # 5) 기업 유저로 전체 지원 조회
    # 기업용 토큰 생성
    comp_list = await async_client.get(
        "/applications/company",
        headers={"Authorization": f"Bearer {comp_user_token}"},
    )  # GET /applications/company
    assert comp_list.status_code == 200  # 조회 성공

    # 6) 상태 변경 테스트 (패치)
    # 먼저 새 지원 생성
    resp2 = await async_client.post(
        "/applications",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"job_posting_id": posting.id},
    )  # 재지원
    new_app = resp2.json()
    new_app_id = new_app["id"]  # 신규 지원 ID

    patch_resp = await async_client.patch(
        f"/applications/company/{new_app_id}/status",
        headers={"Authorization": f"Bearer {comp_user_token}"},
        json={"status": "서류통과"},
    )  # PATCH 상태 변경
    assert patch_resp.status_code == 200  # 수정 성공
    assert patch_resp.json()["status"] == "서류통과"  # 상태 값 확인