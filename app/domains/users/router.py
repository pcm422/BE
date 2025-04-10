from app.domains.users.schemas import UserRead, UserCreate, UserUpdate, UserUpdateRequest
from app.domains.users import service
from app.core.db import get_db_session
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from itsdangerous import SignatureExpired, BadSignature
from app.models.users import User
# from .email.mail_service import serializer, send_verification_email
from sqlalchemy.future import select

from .utiles import create_access_token, get_current_user, create_refresh_token, decode_jwt_token

router = APIRouter(
    prefix="/user",
    tags=["Users"]
)


# 회원가입 API ## 이메일 발송 로직 주석처리해놓음
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
        user_create: UserCreate,  # 클라이언트로부터 전달받은 사용자 생성 정보(UserCreate)
        background_tasks: BackgroundTasks,  # 백그라운드 작업 처리용 BackgroundTasks 객체
        db: AsyncSession = Depends(get_db_session)  # 의존성 주입을 통한 DB 세션(AsyncSession)
):
    """
    회원가입 및 이메일 인증 발송 API.
    사용자가 제공한 정보를 기반으로 신규 사용자를 생성하고 등록된 이메일로 인증 메일을 발송.
    """
    new_user = await service.create_user(db, user_create)  # service.create_user를 호출하여 새 사용자 생성
    # await send_verification_email(background_tasks, new_user.id, new_user.email)  # 새 사용자 이메일로 인증 메일 발송
    return new_user  # 생성된 사용자 객체를 반환


# # 이메일 인증 재요청 API
# @router.post("/send-verify-email")
# async def request_verification_email(
#         user_id: int,  # 클라이언트로부터 전달받은 사용자 ID
#         to_email: str,  # 인증 메일을 받을 이메일 주소
#         background_tasks: BackgroundTasks  # 백그라운드 작업 처리용 객체
# ):
#     """
#     이메일 인증 재요청 API.
#     제공된 사용자 ID와 이메일로 인증 이메일을 재발송.
#     """
#     await send_verification_email(background_tasks, user_id, to_email)  # 이메일 인증 메일 재발송
#     return {"message": "인증 이메일 발송 완료"}  # 성공 메시지 반환


# # 이메일 인증 링크를 통한 사용자 인증 API
# @router.get("/verify-email")
# async def verify_email(
#         token: str = Query(...),  # 쿼리 파라미터로 전달받은 토큰(필수)
#         db: AsyncSession = Depends(get_db_session)  # DB 세션 의존성 주입
# ):
#     """
#     이메일 인증 API.
#     토큰을 검증하여 해당 사용자의 이메일 인증을 완료.
#     """
#     try:
#         user_id = serializer.loads(token, max_age=3600)  # 토큰에서 user_id 추출 (1시간 만료)
#         query = select(User).filter(User.id == user_id)  # user_id로 사용자 조회
#         result = await db.execute(query)  # 쿼리 실행
#         user_obj = result.scalar_one_or_none()  # 단일 사용자 객체 반환 (없으면 None)
#         if not user_obj:  # 사용자 객체가 없으면
#             raise HTTPException(status_code=404, detail="User not found.")  # 404 에러 발생
#         user_obj.is_active = True  # 이메일 인증 완료 설정 (is_active를 True로 변경)
#         db.add(user_obj)  # 변경된 사용자 객체를 DB 세션에 추가
#         await db.commit()  # DB에 변경 사항 커밋
#         await db.refresh(user_obj)  # 최신 상태의 사용자 객체로 갱신
#         return {"message": "이메일 인증 완료"}  # 성공 메시지 반환
#     except SignatureExpired:  # 토큰이 만료된 경우
#         raise HTTPException(status_code=400, detail="토큰이 만료되었습니다.")  # 400 에러 발생
#     except BadSignature:  # 토큰 서명이 올바르지 않을 경우
#         raise HTTPException(status_code=400, detail="잘못된 토큰입니다.")  # 400 에러 발생


# 사용자 로그인 API

@router.post("/login", response_model=dict)
async def login_user(
    email: str = Body(...),
    password: str = Body(...),
    db: AsyncSession = Depends(get_db_session)
):
    """
    사용자 로그인 API.
    제공된 이메일과 비밀번호를 검증 후 JWT 토큰을 발급.
    """
    user = await service.login_user(db, email, password)
    # JWT 토큰 생성 시, 보통 user id를 sub(subject)로 포함합니다.
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return {
        "status": "success",
        "message": "로그인에 성공하셨습니다.",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }
    }


@router.post("/refresh")
async def refresh_token(
        refresh_token: str = Body(...),
        db: AsyncSession = Depends(get_db_session)
):
    """
    Refresh 토큰을 받아서 새 Access 토큰을 발급해주는 API
    """
    try:
        payload = decode_jwt_token(refresh_token)  # token_type이 'refresh'인지 확인
        if payload.get("token_type") != "refresh":
            raise HTTPException(status_code=400, detail="Refresh 토큰이 아닙니다.")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰(sub 누락).")

        # (선택) DB에서 사용자 조회하여 탈퇴/정지 상태가 아닌지 확인
        user = await service.get_user_by_id(db, int(user_id))
        if not user:
            raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

        # 새 Access 토큰 생성
        new_access_token = create_access_token({"sub": user_id})
        return {
            "status": "success",
            "message": "새로운 Access 토큰이 발급되었습니다.",
            "data": {
                "access_token": new_access_token
            }
        }
    except ValueError as e:
        # decode_jwt_token에서 발생한 에러 처리
        raise HTTPException(status_code=401, detail=str(e))

# 사용자 로그아웃 API
@router.post("/logout")
async def logout_user(current_user: dict = Depends(get_current_user)):
    """
    사용자 로그아웃 API.
    JWT로 인증된 사용자만 로그아웃 요청 가능.
    """
    return {"status": "success", "message": "로그아웃이 정상적으로 처리되었습니다."} # 상태, 메세지 반환


# 사용자 정보 조회 API
@router.get("/{user_id}", response_model=UserRead)  # GET /{user_id} API, 응답 타입은 UserRead
async def read_user(
    user_id: int,  # URL 경로에서 추출한 사용자 ID
    current_user: dict = Depends(get_current_user),   # 토큰 검증
    db: AsyncSession = Depends(get_db_session)
):
    """
    사용자 정보 조회 API.
    주어진 사용자 ID에 해당하는 정보를 조회하여 반환.
    """
    user = await service.get_user_by_id(db, user_id)  # service.get_user_by_id 호출하여 사용자 조회
    return user  # 조회된 사용자 객체 반환


# 사용자 정보 수정 API (비밀번호 포함 업데이트 가능)
@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
        user_id: int,  # URL 경로에 담긴 사용자 ID
        payload: UserUpdateRequest = Body(...),
        current_user: dict = Depends(get_current_user),  # 토큰 검증
        db: AsyncSession = Depends(get_db_session)  # DB 세션 의존성 주입
):
    """
    사용자 정보 수정 API.
    수정하고 싶은 항목만 수정 가능
    새 비밀번호(new_password)가 있을경우 새 비밀번호 확인(confirm_password)하고 일치하는지 검증 후에
    나머지 업데이트 데이터와 함께 수정
    """
    # 새 비밀번호 관련 필드를 payload에서 추출
    new_password = payload.new_password
    confirm_password = payload.confirm_password

    if new_password is not None:
        # 새 비밀번호가 있으면, 확인 필드와 일치하는지 검증
        if new_password != confirm_password:
            raise HTTPException(status_code=400, detail="비밀번호와 확인 비밀번호가 일치하지 않습니다.")

    # payload에서 새 비밀번호 필드를 제외한 값들만 추출하여 UserUpdate로 활용
    update_data = payload.dict(exclude={"new_password", "confirm_password"}, exclude_unset=True)
    user_update = UserUpdate(**update_data)

    updated_user = await service.update_user(db, user_id, user_update, new_password=new_password)
    return updated_user

# 비밀번호 재설정 API (비밀번호 분실 시)
@router.post("/reset-password", response_model=dict)
async def reset_password(
        name: str = Body(...),  # 사용자 이름
        email: str = Body(...),  # 사용자 이메일
        new_password: str = Body(...),  # 새 비밀번호
        confirm_password: str = Body(...),  # 새 비밀번호 확인
        db: AsyncSession = Depends(get_db_session)  # DB 세션 의존성 주입
):
    """
    비밀번호 재설정 API.
    제공된 이름과 이메일로 사용자를 조회하여, 새 비밀번호를 해싱 처리 후 수정.
    """
    if new_password != confirm_password:  # 새 비밀번호와 확인 비밀번호가 일치하는지 검증
        raise HTTPException(status_code=400, detail="비밀번호와 확인 비밀번호가 일치하지 않습니다.")  # 일치하지 않으면 400 에러 발생
    user_obj = await service.reset_password(db, name, email, new_password)  # service.reset_password 호출하여 비밀번호 재설정
    return {"message": "비밀번호가 재설정되었습니다."}  # 성공 메시지 반환


# 회원 탈퇴 API
@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
        user_id: int,  # URL 경로에서 추출한 삭제할 사용자 ID
        current_user: dict = Depends(get_current_user), # 토큰 검증
        db: AsyncSession = Depends(get_db_session)  # DB 세션 의존성 주입
):
    """
    회원 탈퇴 API.
    주어진 사용자 ID에 해당하는 계정을 삭제.
    """
    await service.delete_user(db, user_id)  # service.delete_user 호출하여 사용자 삭제
    return {"message": "회원 정보가 정상적으로 삭제되었습니다."}  # 삭제 성공 메시지 반환