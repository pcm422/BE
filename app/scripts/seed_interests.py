import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import AsyncSessionFactory
from app.models.interests import Interest

INTERESTS = [
    {"code": "office", "name": "사무"},
    {"code": "service", "name": "서비스"},
    {"code": "tech", "name": "기술직"},
    {"code": "education", "name": "교육/강사"},
    {"code": "public", "name": "서울시 공공일자리"},
    {"code": "driver", "name": "운전/배송"},
    {"code": "etc", "name": "기타"},
]

async def seed():
    async with AsyncSessionFactory() as session:  # db 세션 시작
        for item in INTERESTS:
            exists = await session.execute(
                Interest.__table__.select().where(Interest.code == item["code"])
            )
            if not exists.first():
                session.add(Interest(**item, is_custom=False))
        await session.commit()
        print("✅ 관심분야 시드 데이터 삽입 완료!")

if __name__ == "__main__":
    asyncio.run(seed())


'''
docker compose exec app bash
# 컨테이너 내부에서
PYTHONPATH=/app poetry run python app/scripts/seed_interests.py
'''