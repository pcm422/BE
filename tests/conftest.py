# ...existing code...
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.db import get_db_session
from app.models.base import Base
from app.core import config

# 테스트용 데이터베이스 URL (예: 기존 DB URL에 _test 추가)
TEST_DATABASE_URL = config.DATABASE_URL + "_test"

# 테스트용 비동기 엔진 및 세션 메이커
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession
)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """테스트 세션 시작 시 DB 테이블 생성, 종료 시 삭제"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await test_engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """각 테스트 함수마다 새로운 DB 세션 제공"""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """비동기 HTTP 클라이언트 제공 및 DB 세션 오버라이드"""
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
# ...existing code...