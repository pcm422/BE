from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class Interest(Base):
    __tablename__ = "interests"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)  # 예: "office"
    name = Column(String(100), nullable=False)  # 예: "사무"
    is_custom = Column(Boolean, default=False)  # 사용자 정의 항목 여부

    user_interests = relationship(
        "UserInterest", back_populates="interest", cascade="all, delete-orphan"
    )

    def __str__(self):
        return self.name