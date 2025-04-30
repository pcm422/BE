from sqlalchemy.future import select
from datetime import datetime, timedelta

from app.core.db import AsyncSessionFactory
from app.models import User, CompanyUser
from app.models.users import EmailVerification


async def delete_unverified_users():
    async with AsyncSessionFactory() as session:
        minutes_ago = datetime.now() - timedelta(minutes=5) # --> 일단 5분 이상되면

        # 일반 사용자 삭제
        result = await session.execute(
            select(User).where(
                User.is_active == False,
                User.created_at <= minutes_ago
            )
        )
        users = result.scalars().all()
        for user in users:
            await session.delete(user)

        # 기업 사용자 삭제
        result = await session.execute(
            select(CompanyUser).where(
                CompanyUser.is_active == False,
                CompanyUser.created_at <= minutes_ago
            )
        )
        company_users = result.scalars().all()
        for cu in company_users:
            await session.delete(cu)

        # 이메일 인증 요청 만료 레코드 삭제
        result = await session.execute(
            select(EmailVerification).where(
                EmailVerification.is_verified == False,
                EmailVerification.expires_at <= minutes_ago
            )
        )
        expired_verifications = result.scalars().all()
        for ev in expired_verifications:
            await session.delete(ev)

        if users or company_users:
            await session.commit()