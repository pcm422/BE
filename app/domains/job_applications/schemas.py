from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.job_applications import ApplicationStatusEnum

class ResumeApplyCreate(BaseModel):
    """사용자가 이력서를 채용공고에 지원할 때 사용하는 입력"""
    job_posting_id: int = Field(..., description="지원할 채용공고 ID")

class JobApplicationStatusUpdate(BaseModel):
    """기업이 지원 상태를 변경할 때 사용하는 입력"""
    status: ApplicationStatusEnum = Field(..., description="변경할 지원 상태")

class JobApplicationRead(BaseModel):
    """지원 내역 단건 조회·생성 응답용"""
    id: int                          # 지원 PK
    user_id: int                     # 지원자 사용자 PK
    job_posting_id: int              # 지원된 채용공고 PK
    resumes_data: dict = Field(..., description="지원 시점 이력서 데이터")
    status: ApplicationStatusEnum    # 지원 상태
    email_sent: Optional[bool] = Field(default=True, description="이메일 발송 성공 여부 (기본 True)") # 이메일 발송 여부
    created_at: datetime             # 생성 시각
    updated_at: datetime             # 수정 시각

    class Config:
        from_attributes = True              # ORM 객체를 Pydantic 모델로 읽어올 때 필요