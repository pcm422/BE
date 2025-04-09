from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator
from app.core.config import DATABASE_URL

# DB URL 설정 확인
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았거나 .env 파일 로드에 실패했습니다.")

# 비동기 DB 엔진 생성
engine = create_async_engine(DATABASE_URL, echo=True)

# 비동기 세션 메이커 생성 (async_sessionmaker 사용 권장)
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False, # 기본값이 False라 생략 가능
    autoflush=False,  # 기본값이 False라 생략 가능
)

# 의존성 주입용 비동기 DB 세션 제공 함수 (async with 사용 예시)
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 의존성 주입용 비동기 DB 세션 생성기 (async with 사용)"""
    async with AsyncSessionFactory() as session:
        try:
            # 세션을 라우트 함수 등에 전달
            yield session
            # 여기서 자동 커밋하지 않음
        except Exception:
            # 예외 발생 시 롤백 (async with가 자동으로 처리하지만 명시해도 무방)
            await session.rollback()
            # 에러 로깅 등을 여기에 추가
            raise # 예외를 다시 발생시켜 FastAPI가 처리하도록 함
        # finally에서 close는 async with가 자동으로 처리해줌