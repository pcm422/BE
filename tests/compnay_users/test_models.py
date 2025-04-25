import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 여러분의 모델과 Base를 가져옵니다
from app.models.base import Base
from app.models.company_info import CompanyInfo
from app.models.company_users import CompanyUser

@pytest.fixture(scope="module")
def db_session():
    # 1) 메모리 SQLite 엔진 & 세션 팩토리 생성
    engine = create_engine("sqlite:///:memory:", echo=False)
    Session = sessionmaker(bind=engine)

    # 2) 테이블 생성
    Base.metadata.create_all(engine)
    session = Session()
    yield session

    # 3) 세션 닫고, 테이블 드롭
    session.close()
    Base.metadata.drop_all(engine)

def test_companyinfo_model_fields_and_str(db_session):
    # CompanyInfo 인스턴스 생성
    company = CompanyInfo(
        company_name="테스트 회사",
        business_reg_number="1234567890",
        opening_date="20210101",
        company_intro="테스트용 회사 소개글입니다.",
        ceo_name="신혜지",
        manager_name="임효석",
        manager_phone="01012345678",
        manager_email="mgr@test.com",
        address="서울시 양천구",
        company_image="http://example.com/img.png"
    )

    db_session.add(company)
    db_session.commit()           # 동기 커밋
    db_session.refresh(company)   # 동기 리프레시

    # 검증
    assert company.id is not None
    assert company.company_name == "테스트 회사"
    assert company.business_reg_number == "1234567890"
    assert company.address == "서울시 양천구"
    assert str(company) == "테스트 회사"

def test_create_company_user_with_relation(db_session):
    # 1) CompanyInfo 생성
    company = CompanyInfo(
        company_name="관계테스트회사",
        business_reg_number="0987654321",
        opening_date="20230202",
        company_intro="관계를 위한 회사입니다.",
        ceo_name="이대표",
        manager_name="조매니저",
        manager_phone="01087654321",
        manager_email="mgr@relation.com"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    # 2) CompanyUser 생성
    user = CompanyUser(
        email="user@rel.com",
        password="hashed_password",  # 실제 해시는 service 레이어 테스트에서
        company_id=company.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 검증
    assert user.id is not None
    assert user.email == "user@rel.com"
    assert isinstance(user.created_at, datetime)
    assert user.company_id == company.id

    # 관계 검증
    assert user.company.company_name == "관계테스트회사"
    assert user.company_name == "관계테스트회사"  # association_proxy

    # 역참조 검증
    assert any(u.id == user.id for u in company.company_users)

    # __str__ 검증
    assert str(user) == "user@rel.com"