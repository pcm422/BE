import os
import re
import pytest_asyncio
import asyncpg

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient
from app.core.db import get_db_session
from app.models.base import Base
from app.main import app

# 1. 테스트용 데이터베이스 URL 설정
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "") + "_test"

# 2. 테스트 DB용 SQLAlchemy 비동기 엔진 생성
engine = create_async_engine(TEST_DATABASE_URL, future=True)

# 3. 테스트 DB용 비동기 세션 메이커 생성
TestingSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, autocommit=False, autoflush=False
)

# --- 헬퍼 함수 정의 ---

# DB URL에서 데이터베이스 이름 부분만 추출하는 함수
def extract_db_name(url: str) -> str | None:
    match = re.match(r".*//.*:.*@.*/(.*)", url)
    return match.group(1) if match else None

# DB 관리 작업(CREATE/DROP DATABASE)을 위한 관리자 DB 접속 URL 생성 함수
def get_admin_db_url(url: str) -> str:
    # postgresql+asyncpg → postgresql로 바꾸고 DB명은 postgres로 대체
    base_url = url.rsplit("/", 1)[0]
    return base_url.replace("postgresql+asyncpg", "postgresql", 1) + "/postgres"

# 테스트 데이터베이스를 생성하는 비동기 함수 (존재하지 않을 경우)
async def create_test_database(conn, db_name: str):
    existing = await conn.fetch("SELECT datname FROM pg_database;")
    if db_name not in [row["datname"] for row in existing]:
        await conn.execute(f'CREATE DATABASE "{db_name}";')

# 테스트 데이터베이스를 삭제하는 비동기 함수
async def drop_test_database(conn, db_name: str):
    await conn.execute(f'''
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '{db_name}' AND pid <> pg_backend_pid();
    ''')
    await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}";')

# --- pytest fixture 정의 ---

# 전체 테스트 세션 시작 시 DB 환경 설정, 종료 시 정리하는 픽스처
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    # 테스트 DB 이름과 관리자 DB 접속 URL 준비
    db_name = extract_db_name(TEST_DATABASE_URL)
    admin_url = get_admin_db_url(TEST_DATABASE_URL)

    # --- 테스트 시작 전 설정 (Setup) ---
    conn = None # asyncpg 연결 변수 초기화
    try:
        # 관리자 DB에 접속
        conn = await asyncpg.connect(admin_url)
        if db_name:
            await create_test_database(conn, db_name)
        await conn.close()
    except Exception as e:
        print(f"[ERROR] DB 생성 중 오류: {e}")

    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # --- 테스트 실행 시점 ---
    yield
    
    # --- 테스트 종료 후 정리 (Teardown) ---
    # 테이블 삭제
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # DB 삭제
    try:
        conn = await asyncpg.connect(admin_url)
        if db_name:
            await drop_test_database(conn, db_name)
        await conn.close()
    except Exception as e:
        print(f"[ERROR] DB 삭제 중 오류: {e}")

# 각 테스트 함수마다 독립적인 DB 세션을 제공하고 롤백하는 픽스처
@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

# 각 테스트 함수마다 FastAPI 테스트 클라이언트와 DB 의존성 오버라이드를 제공하는 픽스처
@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession):
    # FastAPI의 DB 의존성(get_db_session)을 테스트 세션(db_session)으로 대체하는 함수
    def override_get_db():
        yield db_session

    # FastAPI 앱에 의존성 오버라이드 적용
    app.dependency_overrides[get_db_session] = override_get_db
    
    # 비동기 테스트 클라이언트 생성
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # 테스트 종료 후 적용했던 의존성 오버라이드 제거
    app.dependency_overrides.clear()
