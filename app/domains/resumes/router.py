from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.domains.resumes.schemas import ResumeCreate, ResumeUpdate
from app.domains.resumes.service import (
    serialize_resume,
    get_resume_for_user,
    create_new_resume,
    update_existing_resume,
    delete_resume_by_id
)
from app.domains.users.router import read_current_user

router = APIRouter()

# 현재 사용자의 이력서를 조회함
@router.get("/resumes", tags=["이력서"])
async def get_resume(Authorization: str = Header(...), db: AsyncSession = Depends(get_db_session)):
    # 현재 인증된 사용자 정보를 가져옴
    user = await read_current_user(Authorization=Authorization, db=db)
    # 쿼리 시점에 'selectinload'를 통해 educations 관계를 미리 로드함
    resume = await get_resume_for_user(user.id, db)
    if resume is None:
        raise HTTPException(status_code=404, detail="이력서의 내용을 찾을 수 없습니다.")
    return {"status": "success", "data": serialize_resume(resume)}

# 새로운 이력서를 생성함
@router.post("/resumes", tags=["이력서"])  # HTTP POST 메서드를 라우팅
async def create_resume(
    resume_data: ResumeCreate,              # 이력서 + 학력사항을 포함한 Pydantic 모델
    Authorization: str = Header(...),       # 인증 토큰
    db: AsyncSession = Depends(get_db_session)  # DB 세션 의존성
):
    # 현재 사용자를 토큰으로부터 조회
    user = await read_current_user(Authorization=Authorization, db=db)
    # user_id 검증 (JWT 토큰의 사용자와 요청 바디의 user_id가 동일해야 함)
    if resume_data.user_id != user.id:
        raise HTTPException(status_code=400, detail="사용자 ID가 일치하지 않습니다.")
    new_resume = await create_new_resume(resume_data, db)
    return {"status": "success", "data": serialize_resume(new_resume)}

# 특정 이력서를 수정함
@router.patch("/resumes/{resumes_id}", tags=["이력서"])  # HTTP PATCH 메서드와 경로 파라미터, 태그 지정
async def update_resume(
    resumes_id: int,  # URL 경로에서 이력서 ID 수신
    resume_data: ResumeUpdate,  # 요청 바디에서 수정할 데이터 수신
    Authorization: str = Header(...),  # Authorization 헤더에서 토큰 수신
    db: AsyncSession = Depends(get_db_session)  # DB 세션 의존성 주입
):
    # 현재 인증된 사용자 정보를 가져옴
    user = await read_current_user(Authorization=Authorization, db=db)
    try:
        updated_resume = await update_existing_resume(resumes_id, user.id, resume_data, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail="이력서 수정 중 문제가 발생했습니다.")
    return {"status": "success", "data": serialize_resume(updated_resume)}

# 특정 이력서를 삭제함
@router.delete("/resumes/{resumes_id}", tags=["이력서"])  # HTTP DELETE 메서드와 경로 파라미터, 태그 지정
async def delete_resume(
    resumes_id: int,  # URL 경로에서 삭제할 이력서 ID 수신
    Authorization: str = Header(...),  # Authorization 헤더에서 토큰 수신
    db: AsyncSession = Depends(get_db_session)  # DB 세션 의존성 주입
):
    # 현재 인증된 사용자 정보를 가져옴
    user = await read_current_user(Authorization=Authorization, db=db)
    try:
        await delete_resume_by_id(resumes_id, user.id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success", "message": "이력서가 삭제되었습니다."}