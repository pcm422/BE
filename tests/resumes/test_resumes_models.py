import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Resume, User  # User 모델 추가 임포트
from app.core.utils import hash_password  # 비밀번호 해시 유틸리티 임포트

@pytest.mark.asyncio
async def test_resume_model_create(db_session: AsyncSession):
    # 먼저 유저를 생성하여 저장
    user = User(
        email="testuser@example.com",
        password=hash_password("password1234"),
        name="테스트유저",
        phone_number="010-1234-5678",
        birthday="1990-01-01",
        gender="남성",
        signup_purpose="취업",
        referral_source="지인 소개"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 생성된 유저의 ID를 사용하여 이력서 생성
    resume = Resume(
        user_id=user.id,
        resume_image="https://example.com/image.png",
        desired_area="서울",
        introduction="자기소개입니다."
    )
    db_session.add(resume)
    await db_session.commit()
    await db_session.refresh(resume)

    # 검증
    assert resume.id is not None
    assert resume.desired_area == "서울"
    assert resume.resume_image.startswith("https://")