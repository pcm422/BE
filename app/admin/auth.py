from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from app.core.db import AsyncSessionFactory
from sqlalchemy.future import select
from app.models.admin_users import AdminUser
from app.core.utils import verify_password


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(AdminUser).where(AdminUser.username == username)
            )
            user = result.scalar_one_or_none()

            if user and verify_password(password, user.password):
                request.session.update({"user_id": user.id})
                return True
        return False

    async def logout(self, request: Request):
        request.session.clear()

    async def authenticate(self, request: Request):
        user_id = request.session.get("user_id")
        if not user_id:
            return None

        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(AdminUser).where(AdminUser.id == int(user_id))
            )
            user = result.scalar_one_or_none()

            if user:
                request.state.user = user 
                return user
        return None
