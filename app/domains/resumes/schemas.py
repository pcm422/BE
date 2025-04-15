from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class EducationBase(BaseModel):  # 모든 학력사항 공통 속성
    education_type: str  # 교육 유형 (예: "고등학교", "대학교(4년)" 등)
    school_name: str  # 학교명
    education_status: str  # 학력 상태 (예: "졸업", "재학중", "휴학", "예정")
    start_date: Optional[date] = None  # 입학일, 선택적 필드, 기본값은 None
    end_date: Optional[date] = None  # 졸업(예정)일, 선택적 필드

    class Config:
        orm_mode = True

class EducationCreate(EducationBase):  # EducationBase 상속
    resumes_id: Optional[int] = None

# 교육 이력 수정 요청에 사용할 입력 데이터
class EducationUpdate(BaseModel):
    education_type: Optional[str]  # 교육 유형 (선택적 필드)
    school_name: Optional[str]  # 학교명 (선택적 필드)
    education_status: Optional[str]  # 교육 상태 (선택적 필드)
    start_date: Optional[datetime]  # 입학일 (선택적 필드)
    end_date: Optional[datetime]  # 졸업(예정)일 (선택적 필드)


# 이력서 생성 요청에 사용할 입력 데이터
class ResumeCreate(BaseModel):
    user_id: int                             # 사용자 ID
    resume_image: Optional[str]              # 이력서 이미지
    company_name: Optional[str]              # 회사명
    position: Optional[str]                  # 직급 또는 직무
    work_period_start: Optional[datetime]    # 근무 시작일
    work_period_end: Optional[datetime]      # 근무 종료일
    desired_area: Optional[str]              # 희망 지역
    introduction: Optional[str]              # 자기소개
    educations: Optional[List[EducationCreate]] = None  # 학력사항 리스트

# 이력서 수정 요청에 사용할 입력 데이터
class ResumeUpdate(BaseModel):
    resume_image: Optional[str] = None  # 이력서 이미지 URL
    company_name: Optional[str] = None  # 회사명
    position: Optional[str] = None  # 직무
    work_period_start: Optional[datetime] = None  # 근무 시작일
    work_period_end: Optional[datetime] = None  # 근무 종료일
    desired_area: Optional[str] = None  # 희망 지역
    introduction: Optional[str] = None  # 자기소개 내용
    educations: Optional[List[EducationUpdate]] = None  # 학력사항 수정 리스트