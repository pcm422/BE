import logging # 로깅 모듈 임포트
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.core.config import DATABASE_URL

# DB URL 설정 확인
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL 환경 변수가 설정되지 않았거나 .env 파일 로드에 실패했습니다."
    )

logger = logging.getLogger(__name__) # 로거 인스턴스 생성

# 비동기 DB 엔진 생성 시 pool_recycle 옵션 추가
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 프로덕션에서는 False
    pool_recycle=600
)

# 비동기 세션 메이커 생성 (async_sessionmaker 사용 권장)
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,  # 기본값이 False라 생략 가능
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
        except Exception as e: # 예외 객체 받기
            logger.error(f"DB Session rollback due to exception: {e}", exc_info=True)
            # 예외 발생 시 롤백 (async with가 자동으로 처리하지만 명시해도 무방)
            await session.rollback()
            raise  # 예외를 다시 발생시켜 FastAPI가 처리하도록 함
        # finally에서 close는 async with가 자동으로 처리해줌
