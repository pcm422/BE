from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select # SQLAlchemy 2.0 스타일 쿼리 사용

from app.core.db import get_db_session
from app.models.users import User as UserModel
from app.domains.users import schemas

# 라우터 객체 생성
router = APIRouter()

# 사용자 생성 API (POST /users/)
@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: schemas.UserCreate, # 요청 본문은 UserCreate 스키마로 받음
    db: AsyncSession = Depends(get_db_session) # 비동기 세션 주입
):
    """
    새로운 사용자를 생성합니다.

    - **email**: 사용자 이메일 (고유해야 함)
    - **password**: 사용자 비밀번호 (요청 시에만 필요)
    """
    # 이미 존재하는 이메일인지 확인 
    result = await db.execute(select(UserModel).filter(UserModel.email == user_in.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 이메일입니다.",
        )

    # UserModel 객체 생성 (주의: 실제로는 비밀번호 해싱 필요!)
    db_user = UserModel(email=user_in.email, password=user_in.password)

    # 데이터베이스에 추가 및 커밋
    db.add(db_user)
    await db.commit() # 여기서 명시적으로 커밋!
    await db.refresh(db_user) # DB에 저장된 정보(예: 자동 생성된 ID)로 객체 업데이트

    # 생성된 사용자 정보 반환 (User 스키마에 따라 비밀번호 제외)
    return db_user

# 사용자 조회 API (GET /users/{user_id})
@router.get("/{user_id}", response_model=schemas.User)
async def read_user(
    user_id: int, # 경로 매개변수로 사용자 ID 받음
    db: AsyncSession = Depends(get_db_session) # 비동기 세션 주입
):
    """
    주어진 ID의 사용자 정보를 조회합니다.
    """
    # SQLAlchemy 비동기 쿼리
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    db_user = result.scalar_one_or_none() # 결과가 하나거나 없으면 None 반환

    # 사용자가 없으면 404 에러 발생
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    # 조회된 사용자 정보 반환
    return db_user