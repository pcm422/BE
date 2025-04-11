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
            result = await session.execute(select(AdminUser).where(AdminUser.username == username))
            user = result.scalar_one_or_none()

            if user and verify_password(password, user.password):
                request.session.update({"token": f"admin-{user.id}"})
                return True
        return False

    async def logout(self, request: Request):
        request.session.clear()

    async def authenticate(self, request: Request):
        token = request.session.get("token")
        if token and token.startswith("admin-"):
            return token
        return None
