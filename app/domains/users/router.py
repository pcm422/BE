import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db_session
from app.models import User, UserInterest

from app.domains.users.schemas import (
    TokenRefreshRequest,
    UserLogin,
    UserProfileUpdate,
    UserRegister,
    FindEmailRequest,
    PasswordResetConfirmResponse,
    PasswordResetverify,
    PasswordResetVerifyResponse,
    PasswordResetConfirmRequest
)
from .service import (
    ALGORITHM,
    SECRET_KEY,
    delete_user,
    get_user_details,
    login_user,
    recommend_jobs,
    refresh_access_token,
    register_user,
    update_user,
    find_my_email_user_info,
    reset_password_after_verification,
    verify_user_reset_password, check_email_is_verified,
)
from app.core.email_utils.mail_service import verify_user_email, handle_verification_email

router = APIRouter()

# 이메일 인증 여부 확인
@router.get("/auth/check-verification", tags=["인증"])
async def check_email_verified(
    email: str = Query(..., description="확인할 이메일 주소"),
    user_type: str = Query(..., regex="^(user|company)$", description="사용자 유형 (user 또는 company)"),
    db: AsyncSession = Depends(get_db_session)
):
    verification = await check_email_is_verified(email, user_type, db)

    return {
        "status": "success",
        "message": "이메일 인증이 완료된 상태입니다.",
        "data": {
            "email": verification.email,
            "user_type": verification.user_type,
            "expires_at": verification.expires_at.isoformat(),
            "is_verified": verification.is_verified,
        },
    }

# 이메일 인증 요청
@router.post("/auth/verification", tags=["인증"])
async def request_email_verification(
    background_tasks : BackgroundTasks,
    email: str = Query(..., description="이메일 인증을 요청할 주소"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    이메일 인증을 요청하는 엔드포인트입니다.
    이메일 중복 여부를 확인하고 인증 메일을 전송합니다.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")

    await handle_verification_email(background_tasks, email, db, user_type="user")
    return {"status": "success", "message": "인증 이메일이 전송되었습니다."}


# 인증된 현재 사용자 의존성 확인
@router.get("/user/me", tags=["사용자"])
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
        select(User)
        .options(selectinload(User.user_interests).selectinload(UserInterest.interest))
        .filter(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()  # 조회된 사용자 객체 반환 또는 예외 발생
    if user is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return user  # 조회된 사용자 객체 반환

# 회원가입
@router.post("/user/register", tags=["사용자"])
async def register(
    user_data: UserRegister,
    background_tasks: BackgroundTasks,
    db=Depends(get_db_session),
):
    """
    새로운 사용자를 등록하는 엔드포인트입니다.
    이메일 인증이 완료된 사용자만 회원가입이 가능합니다.
    """
    result = await register_user(db, user_data)
    return result

# 로그인
@router.post("/user/login", tags=["사용자"])
async def login(user_credentials: UserLogin, db=Depends(get_db_session)):
    """
    사용자가 로그인하는 엔드포인트입니다.
    사용자 자격 증명을 받아 로그인 비즈니스 로직을 호출합니다.
    """
    result = await login_user(db, user_credentials)  # service의 login_user 호출
    return result  # 결과 반환

# 이메일 인증
@router.get("/verify-email")
async def verify_email(
    token: str,
    user_type: str = Query(..., description="인증 대상 구분: user 또는 company"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    사용자가 이메일을 인증하는 엔드포인트입니다.
    사용자가 회원가입한 이메일로 메일 상 "인증하기" 버튼을 누르면 is_active가 활성화됩니다.
    """
    return await verify_user_email(token, user_type=user_type, db=db)

# 로그아웃
@router.post("/user/logout", tags=["사용자"])
async def logout():
    """
    사용자가 로그아웃하는 엔드포인트입니다.
    JWT 기반의 로그아웃 처리로, 단순 성공 메시지를 반환합니다.
    """
    # (실제 운영에서는 토큰 블랙리스트 관리 등 추가 검증 필요)
    return {"status": "success", "message": "로그아웃이 정상적으로 처리되었습니다."}


# 사용자 프로필 업데이트
@router.patch("/user/{user_id}", tags=["사용자"])
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
@router.delete("/user/{user_id}", tags=["사용자"])
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
@router.post("/auth/refresh-token", tags=["인증"])
async def refresh_token(token_data: TokenRefreshRequest, db=Depends(get_db_session)):
    """
    리프레쉬 토큰을 사용하여 새로운 액세스 토큰을 발급하는 엔드포인트입니다.
    리프레쉬 토큰 정보를 받아 액세스 토큰 재발급 비즈니스 로직을 호출합니다.
    """
    result = await refresh_access_token(
        db, token_data
    )  # service의 refresh_access_token 호출
    return result  # 결과 반환

# 관심분야 기반 추천 채용공고 제공
@router.get("/user/recommend", tags=["사용자"])
async def recommend(
    current_user: User = Depends(read_current_user), db=Depends(get_db_session)
):
    """
    사용자에게 추천 채용공고를 제공하는 엔드포인트입니다.
    현재 사용자의 정보를 받아 추천 비즈니스 로직을 호출합니다.
    """
    result = await recommend_jobs(db, current_user)  # service의 recommend_jobs 호출
    return result  # 결과 반환


# 사용자 정보 조회
@router.get("/user/{user_id}", tags=["사용자"])
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


# 비밀번호 재설정 시 사용자 인증 API
@router.post("/user/password/verify", tags=["사용자"], response_model=PasswordResetVerifyResponse)
async def password_reset_verify(
    payload: PasswordResetverify,  # 인증 요청 데이터
    db: AsyncSession = Depends(get_db_session)  # DB 세션 주입
):
    """
    비밀번호 재설정을 위한 사용자 인증
    이메일, 이름, 전화번호, 생년월일을 검증하여 user_id를 반환합니다.
    """
    return await verify_user_reset_password(db, payload)

# 비밀번호 재설정 API
@router.post("/user/password/reset", tags=["사용자"], response_model=PasswordResetConfirmResponse)
async def password_reset_confirm(
    payload: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    비밀번호 재설정 API
    user_id, new_password, confirm_password를 받아 비밀번호를 최종 변경합니다.
    """
    return await reset_password_after_verification(
        db=db,
        user_id=payload.user_id,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password
    )

@router.post("/user/find_email", tags=["사용자"])
async def find_email(payload: FindEmailRequest,db=Depends(get_db_session)):
    """
    이름, 전화번호, 생년월일을 이용해 가입된 이메일을 찾습니다.
    """
    return await find_my_email_user_info(
        db=db,
        name=payload.name,
        phone_number=payload.phone_number,
        birthday=payload.birthday
    )