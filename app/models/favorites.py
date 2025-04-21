from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

# 유틸리티 함수 임포트
from app.core.datetime_utils import get_now_kst
from app.models.base import Base


class Favorite(Base):
    __tablename__ = "favorite"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_now_kst) # 유틸리티 함수 사용

    # 관계
    user = relationship("User", back_populates="favorites")
    job_posting = relationship("JobPosting", back_populates="favorites")

    def __str__(self):
        return f"{self.id} - {self.created_at}"