import asyncio
from app.core.db import AsyncSessionFactory
from app.models.admin_users import AdminUser
from app.core.utils import hash_password

USERNAME = "admin"
PASSWORD = "Wehavea00!"

async def create_superuser():
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            AdminUser.__table__.select().where(AdminUser.username == USERNAME)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"❗️이미 존재하는 어드민: {USERNAME}")
            return

        hashed_pw = hash_password(PASSWORD)
        admin = AdminUser(
            username=USERNAME,
            password=hashed_pw,
            is_superuser=True  # ❗ 상위 어드민!
        )
        session.add(admin)
        await session.commit()
        print(f"✅ 상위 어드민 계정 생성 완료: {USERNAME}")

if __name__ == "__main__":
    asyncio.run(create_superuser())


'''
docker compose exec app bash
# 컨테이너 내부에서
PYTHONPATH=/app poetry run python app/scripts/create_superuser.py
'''