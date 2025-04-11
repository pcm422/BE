from sqlalchemy import Boolean, Column, Integer, String
from app.models.base import Base

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # 해시 저장
    is_superuser = Column(Boolean, nullable=False, default=False)