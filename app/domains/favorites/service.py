from fastapi import HTTPException, status  # HTTP 예외 처리 및 상태 코드 임포트
from sqlalchemy.ext.asyncio import AsyncSession  # 비동기 DB 세션 사용
from sqlalchemy.future import select  # 비동기 쿼리 작성을 위해 select 임포트

# 해당 모델들은 기존에 정의된 Favorite, JobPosting, User 모델입니다.
from app.models import Favorite, JobPosting, User


# 즐겨찾기 생성 함수
async def create_favorite(
    db: AsyncSession, current_user: User, job_posting_id: int
) -> Favorite:
    # 1. 동일 채용공고가 이미 즐겨찾기에 추가되어 있는지 확인합니다.
    query = select(Favorite).where(
        Favorite.user_id == current_user.id, Favorite.job_posting_id == job_posting_id
    )
    result = await db.execute(query)
    existing_fav = result.scalar_one_or_none()  # 기존 즐겨찾기 존재 여부 확인
    if existing_fav:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 즐겨찾기에 추가된 채용공고입니다.",
        )
    # 2. 채용공고가 실제로 존재하는지 확인합니다.
    job_query = select(JobPosting).where(JobPosting.id == job_posting_id)
    job_result = await db.execute(job_query)
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="채용공고를 찾을 수 없습니다."
        )
    # 3. 즐겨찾기 레코드 생성
    new_fav = Favorite(
        user_id=current_user.id,
        job_posting_id=job_posting_id,
    )
    db.add(new_fav)  # 새 레코드를 세션에 추가
    await db.commit()  # 변경사항 커밋
    await db.refresh(new_fav)  # 새 레코드 최신 상태 반영
    return new_fav  # 생성된 즐겨찾기 객체 반환


# 즐겨찾기 삭제 함수
async def delete_favorite(
    db: AsyncSession, current_user: User, job_posting_id: int
) -> None:
    # 현재 사용자와 해당 채용공고에 해당하는 즐겨찾기 레코드를 조회합니다.
    query = select(Favorite).where(
        Favorite.user_id == current_user.id, Favorite.job_posting_id == job_posting_id
    )
    result = await db.execute(query)
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="즐겨찾기에 등록된 채용공고가 없습니다.",
        )
    await db.delete(fav)  # 레코드 삭제
    await db.commit()  # 커밋


# 즐겨찾기 목록 조회 함수
async def list_favorites(db: AsyncSession, current_user: User) -> list:
    # 현재 사용자의 즐겨찾기 목록을 조회합니다.
    query = select(Favorite).where(Favorite.user_id == current_user.id)
    result = await db.execute(query)
    fav_list = result.scalars().all()  # 즐겨찾기 레코드 목록
    favorites = []  # 응답 목록 구성용 리스트
    # 각 즐겨찾기에 대해, 채용공고의 제목을 별도로 조회하여 포함합니다.
    for fav in fav_list:
        job_query = select(JobPosting).where(JobPosting.id == fav.job_posting_id)
        job_result = await db.execute(job_query)
        job = job_result.scalar_one_or_none()
        title = job.title if job else ""
        # 각 즐겨찾기 객체를 FavoriteRead 스키마와 유사한 딕셔너리로 구성합니다.
        favorites.append(
            {
                "id": fav.id,
                "job_posting_id": fav.job_posting_id,
                "created_at": fav.created_at,
                "title": title,
            }
        )
    return favorites
