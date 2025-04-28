import os
import re
import pytest
import pytest_asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.base import Base
from app.core.db import get_db_session

# --- 테스트 DB URL 설정 ---
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "") + "_test"

# --- 헬퍼 함수 ---
def extract_db_name(url: str) -> str | None:
    match = re.match(r".*//.*:.*@.*/(.*)", url)
    return match.group(1) if match else None

def get_admin_db_url(url: str) -> str:
    base_url = url.rsplit("/", 1)[0]
    return base_url.replace("postgresql+asyncpg", "postgresql", 1) + "/postgres"

async def _create_test_database(admin_url: str, db_name: str):
    conn = await asyncpg.connect(admin_url)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            print(f"Creating test database '{db_name}'...")
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()

async def _drop_test_database(admin_url: str, db_name: str):
    conn = await asyncpg.connect(admin_url)
    try:
        print(f"Terminating connections to '{db_name}'...")
        await conn.execute('''
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = $1 AND pid <> pg_backend_pid();
        ''', db_name)
        print(f"Dropping test database '{db_name}'...")
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
    finally:
        await conn.close()

# --- 세션 스코프: DB 생성/삭제 ---
@pytest_asyncio.fixture(scope="session", autouse=True)
async def manage_test_database():
    db_name = extract_db_name(TEST_DATABASE_URL)
    admin_url = get_admin_db_url(TEST_DATABASE_URL)
    if not db_name:
        pytest.fail("Could not extract database name from TEST_DATABASE_URL")
    print("\n--- Setting up test database ---")
    await _create_test_database(admin_url, db_name)
    yield
    print("\n--- Tearing down test database ---")
    await _drop_test_database(admin_url, db_name)

# --- 함수 스코프: 엔진 생성/폐기 ---
@pytest_asyncio.fixture(scope="function")
async def db_engine(manage_test_database):
    engine = create_async_engine(TEST_DATABASE_URL, future=True, echo=False)
    yield engine
    await engine.dispose()

# --- 함수 스코프: 세션 생성/롤백 ---
@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with TestingSessionLocal() as session:
        yield session

# --- 함수 스코프: async_client 생성 ---
@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
