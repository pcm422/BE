from sqlalchemy import Column, Integer, String
from app.models.base import Base

class User(Base):
    __tablename__ = "users" # 테이블 이름 정의

    id = Column(Integer, primary_key=True, index=True) # 기본 키 (자동 증가)
    email = Column(String, unique=True, index=True, nullable=False) # 이메일 (고유값, 필수)
    password = Column(String, nullable=False) # 비밀번호 (해싱 안 함, 필수)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"