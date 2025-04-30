import pytest
from app.models.users import User, GenderEnum
from app.core.datetime_utils import get_now_utc
from datetime import datetime

def test_user_model_fields():
    # 사용자 객체 생성
    user = User(
        name="홍길동",  # 사용자 이름
        email="test@example.com",  # 이메일
        password="hashedpassword",  # 비밀번호
        phone_number="010-1234-5678",  # 전화번호
        birthday="1990-01-01",  # 생년월일
        gender=GenderEnum.male,  # 성별
        signup_purpose="정보 탐색",  # 가입 목적
        referral_source="블로그",  # 유입 경로
        is_active=True,  # 활성 상태
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    # 필드 검증
    assert user.name == "홍길동"
    assert user.email == "test@example.com"
    assert user.password == "hashedpassword"
    assert user.phone_number == "010-1234-5678"
    assert user.birthday == "1990-01-01"
    assert user.gender == GenderEnum.male
    assert user.signup_purpose == "정보 탐색"
    assert user.referral_source == "블로그"
    assert user.is_active is True

    # 자동 생성 필드 검증
    assert user.created_at is not None
    assert user.updated_at is not None
    assert isinstance(user.created_at, type(get_now_utc()))
    assert isinstance(user.updated_at, type(get_now_utc()))


def test_gender_enum():
    # Enum 값 확인
    assert GenderEnum.male.value == "남성"
    assert GenderEnum.female.value == "여성"
    assert str(GenderEnum.male) == "GenderEnum.male"
