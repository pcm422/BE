import os
import asyncio
from logging.config import fileConfig

# SQLAlchemy 비동기 엔진 및 풀 관련 임포트
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool

# Alembic 컨텍스트 임포트
from alembic import context

# --- 프로젝트 특정 설정 시작 ---
# 프로젝트 루트 경로 추가 (app 모듈 임포트 위함)
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# 환경 변수에서 데이터베이스 URL 로드 (PostgreSQL 연결 정보)
from app.core.config import DATABASE_URL
# 모든 SQLAlchemy 모델의 Base 메타데이터 임포트
from app.models.base import Base
# --- 프로젝트 특정 설정 끝 ---

# Alembic 설정 객체 (alembic.ini 값 접근용)
config = context.config

# Python 로깅 설정 (alembic.ini 파일 참조)
if config.config_file_name is not None:
    fileConfig(config.config_file_name) # 로거 설정

# 마이그레이션 대상 메타데이터 설정
# Base.metadata 사용: app/models 아래 모든 테이블 자동 감지 ('autogenerate' 지원)
target_metadata = Base.metadata
# target_metadata = None # 특정 메타데이터 사용 안 할 경우

# 기타 alembic.ini 옵션 로드 예시 (필요시 사용)
# my_important_option = config.get_main_option("my_important_option")

# 오프라인 마이그레이션 실행 함수 정의
def run_migrations_offline() -> None:
    """'오프라인' 모드 마이그레이션 실행 로직.

    DB 연결 없이 SQL 스크립트 생성 시 사용.
    Engine 생성 건너뛰므로 DBAPI 불필요.
    context.execute() 호출 시 SQL 문자열을 출력.
    """
    # url = config.get_main_option("sqlalchemy.url") # 기존 .ini 파일 방식 주석 처리
    url = DATABASE_URL # 환경 변수에서 직접 DB URL 사용
    context.configure(
        url=url, # 사용할 DB URL
        target_metadata=target_metadata, # 마이그레이션 대상 테이블 메타데이터
        literal_binds=True, # SQL문에 파라미터 값을 직접 포함 (오프라인 모드용)
        dialect_opts={"paramstyle": "named"}, # SQL 방언 옵션
    )

    # 트랜잭션 내에서 마이그레이션 실행 (스크립트 생성)
    with context.begin_transaction():
        context.run_migrations()

# 실제 마이그레이션 실행 담당 동기 함수
def do_run_migrations(connection):
    # 전달받은 DB 연결(connection)과 메타데이터로 컨텍스트 설정
    context.configure(connection=connection, target_metadata=target_metadata)

    # 트랜잭션 내에서 실제 DB에 마이그레이션 실행
    with context.begin_transaction():
        context.run_migrations()

# 온라인 마이그레이션 실행 함수 정의 (비동기 버전)
async def run_migrations_online() -> None:
    """'온라인' 모드 마이그레이션 실행 로직 (비동기).

    실제 DB에 연결하여 마이그레이션 수행.
    비동기 엔진(AsyncEngine) 생성 및 컨텍스트 연결 필요.
    """
    # alembic.ini 파일의 메인 섹션 설정 로드
    configuration = config.get_section(config.config_ini_section)
    # DB URL은 환경 변수 값으로 덮어쓰기
    configuration['sqlalchemy.url'] = DATABASE_URL

    # 비동기 SQLAlchemy 엔진 생성 (FastAPI/psycopg 사용 시 권장)
    connectable = create_async_engine(
        configuration['sqlalchemy.url'], # DB URL 사용
        poolclass=pool.NullPool, # Alembic 실행 시 NullPool 사용 권장
        future=True # SQLAlchemy 2.0 스타일 활성화
    )

    # 비동기 엔진 연결 및 마이그레이션 실행
    async with connectable.connect() as connection: # 비동기 연결 컨텍스트
        # 동기 함수(do_run_migrations)를 비동기 이벤트 루프에서 실행
        await connection.run_sync(do_run_migrations)

    # 비동기 엔진 리소스 정리
    await connectable.dispose()

# 현재 실행 모드 확인 및 해당 함수 호출
if context.is_offline_mode():
    # 오프라인 모드일 경우
    run_migrations_offline()
else:
    # 온라인 모드일 경우 (비동기 실행)
    # run_migrations_online() # 기존 동기 방식 주석 처리
    asyncio.run(run_migrations_online()) # 비동기 온라인 마이그레이션 실행