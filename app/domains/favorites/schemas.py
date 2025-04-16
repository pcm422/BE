from datetime import datetime  # 날짜/시간 처리를 위해 datetime 모듈 임포트

from pydantic import BaseModel, ConfigDict  # Pydantic의 BaseModel을 임포트합니다. 데이터 검증 및 직렬화에 사용


# 즐겨찾기 생성 요청 시 사용할 스키마
class FavoriteCreate(BaseModel):
    # 즐겨찾기에 추가할 채용공고 ID를 받습니다.
    job_posting_id: int  # 필수 정수형 필드


# 즐겨찾기 응답 시 사용할 스키마
class FavoriteRead(BaseModel):
    id: int  # 즐겨찾기 레코드의 고유 ID
    job_posting_id: int  # 즐겨찾기에 추가된 채용공고 ID
    created_at: datetime  # 즐겨찾기 생성 시각
    title: str  # 즐겨찾기에 추가된 채용공고의 제목

    model_config = ConfigDict(from_attributes=True)
