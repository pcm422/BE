from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.domains.users.router import read_current_user
from app.models import User  # User 모델 import

from app.domains.favorites.schemas import FavoriteCreate, FavoriteRead
from app.domains.favorites.service import create_favorite, delete_favorite, list_favorites

router = APIRouter(tags=["즐겨찾기"])  # 즐겨찾기 관련 라우터 생성


# 즐겨찾기 생성 엔드포인트
@router.post(
    "/favorites", status_code=status.HTTP_201_CREATED, response_model=FavoriteRead
)
async def add_favorite(
    fav: FavoriteCreate,  # 요청 본문: 즐겨찾기에 추가할 채용공고 ID
    current_user: User = Depends(
        read_current_user
    ),  # 인증된 현재 사용자, read_current_user를 의존성으로 사용
    db: AsyncSession = Depends(get_db_session),  # 비동기 DB 세션 의존성
):
    new_fav = await create_favorite(db, current_user, fav.job_posting_id)
    from sqlalchemy.future import select

    from app.models import JobPosting

    job_result = await db.execute(
        select(JobPosting).where(JobPosting.id == new_fav.job_posting_id)
    )
    job = job_result.scalar_one_or_none()
    title = job.title if job else ""
    return FavoriteRead(
        id=new_fav.id,
        job_posting_id=new_fav.job_posting_id,
        created_at=new_fav.created_at,
        title=title,
    )


# 즐겨찾기 삭제 엔드포인트
@router.delete("/favorites/{job_posting_id}", response_model=dict)
async def remove_favorite(
    job_posting_id: int,  # URL 경로 파라미터: 삭제할 채용공고 ID
    current_user: User = Depends(read_current_user),  # 인증된 현재 사용자
    db: AsyncSession = Depends(get_db_session),  # 비동기 DB 세션 의존성
):
    # 서비스 계층의 delete_favorite 함수를 호출하여 즐겨찾기 삭제
    await delete_favorite(db, current_user, job_posting_id)
    return {"status": "success", "message": "즐겨찾기에서 제거되었습니다."}


# 즐겨찾기 목록 조회 엔드포인트
@router.get("/favorites", response_model=list[FavoriteRead])
async def get_favorites(
    current_user: User = Depends(read_current_user),  # 인증된 현재 사용자
    db: AsyncSession = Depends(get_db_session),  # 비동기 DB 세션 의존성
):
    # 서비스 계층의 list_favorites 함수를 호출하여 즐겨찾기 목록 조회
    fav_list = await list_favorites(db, current_user)
    # 각 즐겨찾기 딕셔너리를 FavoriteRead 스키마로 변환하여 반환
    # FavoriteRead의 orm_mode 대신 여기서는 직접 필드를 전달합니다.
    return [FavoriteRead(**fav) for fav in fav_list]
