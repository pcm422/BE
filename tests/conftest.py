import os
import re
import uuid

import asyncpg
import pytest
import pytest_asyncio  # 명시적으로 import
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import get_db_session
from app.core.utils import create_access_token
from app.main import app
from app.models import User
from app.models.base import Base
from app.models.users import GenderEnum

# --- 테스트 DB URL 설정  ---
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "") + "_test"


# --- 헬퍼 함수 정의  ---
def extract_db_name(url: str) -> str | None:
    match = re.match(r".*//.*:.*@.*/(.*)", url)
    return match.group(1) if match else None


def get_admin_db_url(url: str) -> str:
    base_url = url.rsplit("/", 1)[0]
    return base_url.replace("postgresql+asyncpg", "postgresql", 1) + "/postgres"


async def create_test_database(conn, db_name: str):
    existing = await conn.fetch("SELECT datname FROM pg_database;")
    if db_name not in [row["datname"] for row in existing]:
        await conn.execute(f'CREATE DATABASE "{db_name}";')


async def drop_test_database(conn, db_name: str):
    await conn.execute(
        f"""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '{db_name}' AND pid <> pg_backend_pid();
    """
    )
    await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}";')


# --- FIXTURE 정의 ---

@pytest_asyncio.fixture(scope="function")
async def db_engine(event_loop):  # ✨ 여기 event_loop 명시 추가!
    """테스트 세션마다 DB 생성 및 삭제"""
    engine = create_async_engine(TEST_DATABASE_URL, future=True)

    db_name = extract_db_name(TEST_DATABASE_URL)
    admin_url = get_admin_db_url(TEST_DATABASE_URL)

    try:
        conn = await asyncpg.connect(admin_url)
        if db_name:
            await create_test_database(conn, db_name)
        await conn.close()
        print(f"테스트 DB '{db_name}' 생성 완료")
    except Exception as e:
        pytest.exit(f"[DB 생성 실패] {e}")

    try:
        async with engine.begin() as conn_engine:
            await conn_engine.run_sync(Base.metadata.create_all)
        print("테이블 생성 완료")
    except Exception as e:
        await engine.dispose()
        pytest.exit(f"[테이블 생성 실패] {e}")

    yield engine

    print("테스트 종료, DB 정리 시작...")
    try:
        async with engine.begin() as conn_engine:
            await conn_engine.run_sync(Base.metadata.drop_all)
        print("테이블 삭제 완료")
    except Exception as e:
        print(f"[테이블 삭제 실패] {e}")

    await engine.dispose()
    print("엔진 종료 완료")

    try:
        conn = await asyncpg.connect(admin_url)
        if db_name:
            await drop_test_database(conn, db_name)
        await conn.close()
        print(f"테스트 DB '{db_name}' 삭제 완료")
    except Exception as e:
        print(f"[DB 삭제 실패] {e}")


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """함수마다 DB 세션 제공"""
    TestingSessionLocal = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession):
    """함수마다 테스트 클라이언트 제공 및 DB 세션 오버라이드"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)  # transport를 직접 사용
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user_token_and_id(db_session):
    """
    랜덤 이메일을 가진 테스트 유저 생성 후 JWT 토큰 발급하는 fixture
    """
    random_email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"

    # 1. 유저를 생성
    user = User(
        name="테스트유저",
        email=random_email,
        password="securepassword",
        gender=GenderEnum.male,
        phone_number="010-1234-5678",
        birthday="1990-01-01",
        signup_purpose="테스트 목적",
        referral_source="구글 검색",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)  # ID값을 가져오기 위해 refresh

    # 2. JWT 토큰 생성 (!!! 여기 반드시 await 해야 함)
    token = await create_access_token(data={"sub": str(user.id)})  # 꼭 sub를 문자열로

    # 3. token, id, email 리턴
    return token, user.id, user.email
