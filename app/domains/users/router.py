import jwt
from fastapi import APIRouter, Depends, Header, HTTPException

from app.core.db import get_db_session
from app.models import User

from .schemas import (PasswordReset, TokenRefreshRequest, UserLogin,
                      UserProfileUpdate, UserRegister)
from .service import (ALGORITHM, SECRET_KEY, delete_user, get_user_details,
                      login_user, recommend_jobs, refresh_access_token,
                      register_user, reset_password, update_user)

router = APIRouter()


# 인증된 현재 사용자 의존성 확인
@router.get("/user/me", tags=["User"])
async def read_current_user(
    Authorization: str = Header(...), db=Depends(get_db_session)
):
    """
    현재 인증된 사용자의 정보를 반환하는 엔드포인트.
    Authorization 헤더에 포함된 JWT 토큰을 검증하여 사용자 정보를 조회.
    """
    # 헤더에서 Bearer 토큰 추출
    if Authorization.startswith("Bearer "):  # "Bearer " 접두사를 포함한 토큰인지 확인
        token = Authorization.split(" ")[1]  # "Bearer " 이후의 실제 토큰 값을 추출
    else:
        raise HTTPException(status_code=401, detail="토큰이 제공되지 않았습니다.")
    try:
        # JWT 토큰 디코딩
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM]
        )  # JWT 토큰을 디코딩하여 payload 추출
        user_id: str = payload.get("sub")  # sub 클레임에서 사용자 ID 추출
        if user_id is None:
            raise HTTPException(status_code=401, detail="잘못된 토큰입니다.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="토큰 검증 실패.")

    from sqlalchemy.future import select

    result = await db.execute(
        select(User).filter(User.id == int(user_id))
    )  # 사용자 ID로 DB에서 사용자 조회
    user = result.scalar_one_or_none()  # 조회된 사용자 객체 반환 또는 예외 발생
    if user is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return user  # 조회된 사용자 객체 반환


# 회원가입
@router.post("/user/register", tags=["User"])
async def register(user_data: UserRegister, db=Depends(get_db_session)):
    """
    새로운 사용자를 등록하는 엔드포인트입니다.
    사용자 정보를 받아 회원가입 비즈니스 로직을 호출합니다.
    """
    result = await register_user(db, user_data)  # service의 register_user 호출
    return result  # 결과 반환


# 로그인
@router.post("/user/login", tags=["User"])
async def login(user_credentials: UserLogin, db=Depends(get_db_session)):
    """
    사용자가 로그인하는 엔드포인트입니다.
    사용자 자격 증명을 받아 로그인 비즈니스 로직을 호출합니다.
    """
    result = await login_user(db, user_credentials)  # service의 login_user 호출
    return result  # 결과 반환


# 로그아웃
@router.post("/user/logout", tags=["User"])
async def logout(Authorization: str = Header(...)):
    """
    사용자가 로그아웃하는 엔드포인트입니다.
    JWT 기반의 로그아웃 처리로, 단순 성공 메시지를 반환합니다.
    """
    # (실제 운영에서는 토큰 블랙리스트 관리 등 추가 검증 필요)
    return {"status": "success", "message": "로그아웃이 정상적으로 처리되었습니다."}


# 사용자 프로필 업데이트
@router.patch("/user/{user_id}", tags=["User"])
async def update(
    user_id: int,
    update_data: UserProfileUpdate,
    current_user: User = Depends(read_current_user),
    db=Depends(get_db_session),
):
    """
    사용자의 프로필 정보를 업데이트하는 엔드포인트입니다.
    사용자 ID와 업데이트할 데이터를 받아 프로필 업데이트 비즈니스 로직을 호출합니다.
    """
    result = await update_user(
        db, user_id, update_data, current_user
    )  # service의 update_user 호출
    return result  # 결과 반환


# 회원 탈퇴
@router.delete("/user/{user_id}", tags=["User"])
async def delete(
    user_id: int,
    current_user: User = Depends(read_current_user),
    db=Depends(get_db_session),
):
    """
    사용자가 회원 탈퇴를 요청하는 엔드포인트입니다.
    사용자 ID를 받아 회원 탈퇴 비즈니스 로직을 호출합니다.
    """
    result = await delete_user(db, user_id, current_user)  # service의 delete_user 호출
    return result  # 결과 반환


# 리프레쉬 토큰을 통한 액세스 토큰 재발급
@router.post("/auth/refresh-token", tags=["Auth"])
async def refresh_token(token_data: TokenRefreshRequest, db=Depends(get_db_session)):
    """
    리프레쉬 토큰을 사용하여 새로운 액세스 토큰을 발급하는 엔드포인트입니다.
    리프레쉬 토큰 정보를 받아 액세스 토큰 재발급 비즈니스 로직을 호출합니다.
    """
    result = await refresh_access_token(
        db, token_data
    )  # service의 refresh_access_token 호출
    return result  # 결과 반환


# 사용자 정보 조회
@router.get("/user/{user_id}", tags=["User"])
async def get_user(
    user_id: int,
    current_user: User = Depends(read_current_user),
    db=Depends(get_db_session),
):
    """
    특정 사용자의 정보를 조회하는 엔드포인트입니다.
    사용자 ID를 받아 사용자 정보 조회 비즈니스 로직을 호출합니다.
    """
    result = await get_user_details(
        db, user_id, current_user
    )  # service의 get_user_details 호출
    return result  # 결과 반환


# 비밀번호 재설정
@router.post("/user/reset-password", tags=["User"])
async def reset_pw(data: PasswordReset, db=Depends(get_db_session)):
    """
    사용자의 비밀번호를 재설정하는 엔드포인트입니다.
    비밀번호 재설정 정보를 받아 비즈니스 로직을 호출합니다.
    """
    result = await reset_password(db, data)  # service의 reset_password 호출
    return result  # 결과 반환


# 관심분야 기반 추천 채용공고 제공
@router.get("/user/recommend", tags=["User"])
async def recommend(
    current_user: User = Depends(read_current_user), db=Depends(get_db_session)
):
    """
    사용자에게 추천 채용공고를 제공하는 엔드포인트입니다.
    현재 사용자의 정보를 받아 추천 비즈니스 로직을 호출합니다.
    """
    result = await recommend_jobs(db, current_user)  # service의 recommend_jobs 호출
    return result  # 결과 반환
