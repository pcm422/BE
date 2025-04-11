from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class Favorite(Base):
    __tablename__ = "favorite"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now)

    # 관계
    user = relationship("User", back_populates="favorites")
    job_posting = relationship("JobPosting", back_populates="favorites")
    
    def __str__(self):
        return f"{self.user.name} - {self.job_posting.title}"