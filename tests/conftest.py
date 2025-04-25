import os
import re
import pytest
import pytest_asyncio # 명시적으로 import
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient

from app.main import app
from app.models.base import Base
from app.core.db import get_db_session

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
    await conn.execute(f'''
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '{db_name}' AND pid <> pg_backend_pid();
    ''')
    await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}";')


# --- pytest fixture 정의 ---

# 세션 스코프에서 DB 생성/삭제 및 엔진 제공
@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """세션당 한 번 실행: 테스트 DB 생성, 엔진 생성 및 제공, 테스트 후 DB 삭제"""
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    db_name = extract_db_name(TEST_DATABASE_URL)
    admin_url = get_admin_db_url(TEST_DATABASE_URL)
    conn = None

    # --- DB 생성 ---
    try:
        conn = await asyncpg.connect(admin_url)
        if db_name:
            await create_test_database(conn, db_name)
        await conn.close()
        print(f"Test database '{db_name}' created (if not exists).")
    except Exception as e:
        print(f"[ERROR] DB 생성 중 오류: {e}")
        pytest.fail(f"Failed to create test database: {e}")

    # --- 테이블 생성 ---
    try:
        async with engine.begin() as conn_engine:
            await conn_engine.run_sync(Base.metadata.create_all)
        print("Tables created.")
    except Exception as e:
        print(f"[ERROR] 테이블 생성 중 오류: {e}")
        await engine.dispose() # 에러 시 엔진 정리 시도
        pytest.fail(f"Failed to create tables: {e}")

    yield engine # 테스트들이 사용할 수 있도록 엔진 객체 반환

    # --- 테스트 종료 후 정리 (Teardown) ---
    print("Starting teardown: Dropping tables and database...")
    # 테이블 삭제 먼저 (엔진 사용)
    try:
        async with engine.begin() as conn_engine:
            await conn_engine.run_sync(Base.metadata.drop_all)
        print("Tables dropped.")
    except Exception as e:
        print(f"[ERROR] 테이블 삭제 중 오류: {e}")

    # 엔진 연결 종료 (DB 삭제 전에)
    await engine.dispose()
    print("Engine disposed.")

    # DB 삭제
    try:
        conn = await asyncpg.connect(admin_url)
        if db_name:
            await drop_test_database(conn, db_name)
        await conn.close()
        print(f"Test database '{db_name}' dropped.")
    except Exception as e:
        print(f"[ERROR] DB 삭제 중 오류: {e}")


# 함수 스코프에서 세션 제공 (세션 스코프의 db_engine 사용)
@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine): # db_engine fixture에 의존
    """함수마다 실행: DB 세션 생성 및 제공, 테스트 후 롤백"""
    # SessionLocal(세션 메이커)를 함수 스코프 내에서 생성
    TestingSessionLocal = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, autocommit=False, autoflush=False
    )
    async with TestingSessionLocal() as session:
        # print(f"DB session {id(session)} created for test function") # 디버깅
        yield session
        # print(f"Rolling back DB session {id(session)}") # 디버깅
        # 테스트 후 자동 롤백 (데이터 초기화)
        await session.rollback()


# 함수 스코프에서 클라이언트 제공 (수정된 db_session 사용)
@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession): # 함수 스코프의 db_session 사용
    """함수마다 실행: 테스트 클라이언트 생성 및 DB 의존성 오버라이드"""
    def override_get_db():
        try:
            yield db_session
        finally:
            # 세션 닫기는 db_session fixture의 컨텍스트 매니저가 처리
            pass

    app.dependency_overrides[get_db_session] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()