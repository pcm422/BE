from pydantic import BaseModel, ConfigDict, Field, field_validator
import re  # 정규식
from typing import Optional, List, TypeVar, Generic
from datetime import date, datetime

from app.models.resumes_educations import EducationTypeEnum, EducationStatusEnum


class EducationBase(BaseModel):  # 모든 학력사항 공통 속성
    education_type: str  # 교육 유형 (예: "고등학교", "대학교(4년)" 등)
    school_name: str  # 학교명
    education_status: str  # 학력 상태 (예: "졸업", "재학중", "휴학", "예정")
    start_date: Optional[date] = None  # 입학일, 선택적 필드, 기본값은 None
    end_date: Optional[date] = None  # 졸업(예정)일, 선택적 필드

    model_config = ConfigDict(from_attributes=True)

# 교육이력 생성 요청에 사용할 입력데이터
class EducationCreate(EducationBase):  # EducationBase 상속
    resumes_id: Optional[int] = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_month_only_date(cls, value):
        if isinstance(value, str) and re.match(r"^\d{4}-\d{2}$", value):
            return f"{value}-01"
        return value

# 경력 생성 요청에 사용할 입력데이터
class ExperienceCreate(BaseModel):
    company_name: str = Field(..., description="회사명")  # 회사명(경력)
    position: str = Field(..., description="직무/직급")   # 직급(경력)
    start_date: Optional[date] = None   # 시작일(경력)
    end_date: Optional[date] = None  # 종료일(경력)
    description: Optional[str] = None  # 내용(경력)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_month_only_date(cls, value):
        if isinstance(value, str) and re.match(r"^\d{4}-\d{2}$", value):
            return f"{value}-01"
        return value

# 교육 이력 수정 요청에 사용할 입력 데이터
class EducationUpdate(BaseModel):
    id: Optional[int] = None
    education_type: Optional[str]  # 교육 유형
    school_name: Optional[str]  # 학교명
    education_status: Optional[str]  # 교육 상태
    start_date: Optional[datetime]  # 입학일
    end_date: Optional[datetime]  # 졸업(예정)일

# 경력 이력 수정 요청에 사용할 입력 데이터
class ExperienceUpdate(BaseModel):
    id: Optional[int] = None   # 이력서 아이디
    company_name: Optional[str] = None   # 회사명
    position: Optional[str] = None  # 직급
    start_date: Optional[date] = None  # 시작일
    end_date: Optional[date] = None  # 종료일
    description: Optional[str] = None  # 설명

# 이력서 생성 요청에 사용할 입력 데이터
class ResumeCreate(BaseModel):
    user_id: int                             # 사용자 ID
    resume_image: Optional[str]              # 이력서 이미지
    desired_area: Optional[str]              # 희망 지역
    introduction: Optional[str]              # 자기소개
    educations: Optional[List[EducationCreate]] = None  # 학력사항 리스트
    experiences: Optional[List[ExperienceCreate]] = None # 경력사항 리스트

# 이력서 수정 요청에 사용할 입력 데이터
class ResumeUpdate(BaseModel):
    resume_image: Optional[str] = None  # 이력서 이미지 URL
    desired_area: Optional[str] = None  # 희망 지역
    introduction: Optional[str] = None  # 자기소개 내용
    educations: Optional[List[EducationUpdate]] = None  # 학력사항 수정 리스트
    experiences: Optional[List[ExperienceUpdate]] = None # 경력사항 수정 리스트

# 교육 이력 조회 요청에 사용할 입력 데이터
class ResumeEducationRead(BaseModel):
    id:            int  # 학력사항 고유 ID
    resumes_id:    int  # 연결된 이력서 ID
    education_type: EducationTypeEnum  # 교육 유형
    school_name:    str  # 학교명
    education_status: EducationStatusEnum  # 학력 상태
    start_date:    Optional[datetime]  # 입학일
    end_date:      Optional[datetime]  # 졸업(예정)일

    model_config = ConfigDict(from_attributes=True)  # ORM 모드

# 경력 이력 조회 요청에 사용할 입력 데이터
class ResumeExperienceRead(BaseModel):
    id:            int  # 경력사항 고유 ID
    resume_id:     int  # 연결된 이력서 ID
    company_name:  str  # 회사명
    position:      str  # 직무/직급
    description:   Optional[str]  # 업무 내용
    start_date:    Optional[datetime]  # 근무 시작일
    end_date:      Optional[datetime]  # 근무 종료일

    model_config = ConfigDict(from_attributes=True)  # ORM 모드

# 교육 경력 같이 이력서 전체조회 데이터
class ResumeRead(BaseModel):
    id:            int  # 이력서 고유 ID
    user_id:       int  # 작성자 사용자 ID
    resume_image:  Optional[str]  # 이력서 이미지 URL
    desired_area:  Optional[str]  # 희망 근무 지역
    introduction:  Optional[str]  # 자기소개 내용
    # 위에서 정의한 리스트 중첩
    educations:    List[ResumeEducationRead]  = []  # 학력사항 리스트
    experiences:   List[ResumeExperienceRead] = []  # 경력사항 리스트

    model_config = ConfigDict(from_attributes=True)  # ORM 모드

# 공통 응답 래퍼
DataT = TypeVar("DataT")
class BaseResponse(BaseModel, Generic[DataT]):
    status: str
    data:   DataT

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)