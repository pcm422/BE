from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base


class UserInterest(Base):
    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    interest_id = Column(Integer, ForeignKey("interests.id", ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint("user_id", "interest_id", name="uq_user_interest"),
    )

    user = relationship("User", back_populates="user_interests")
    interest = relationship("Interest", back_populates="user_interests")

    def __str__(self):
        return f"{self.user.name} - {self.interest.name}"