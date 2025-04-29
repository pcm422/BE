from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.utils import (
    create_access_token,
    create_refresh_token,
    get_current_company_user,
)
from app.domains.company_users.schemas import (
    CompanyTokenRefreshRequest,
    CompanyUserInfo,
    CompanyUserLoginRequest,
    CompanyUserLoginResponse,
    CompanyUserRegisterRequest,
    CompanyUserRegisterResponse,
    CompanyUserUpdateRequest,
    CompanyUserUpdateResponse,
    FindCompanyUserEmail,
    PasswordResetRequest,
    PasswordResetVerifyRequest,
    PasswordResetVerifyResponse,
    SuccessResponse,
)
from app.domains.company_users.service import (
    check_dupl_business_number,
    check_dupl_email,
    delete_company_user,
    find_company_user_email,
    generate_password_reset_token,
    get_company_user_mypage,
    login_company_user,
    refresh_company_user_access_token,
    register_company_user,
    reset_password_with_token,
    update_company_user,
)
from app.domains.company_users.utiles import success_response
from app.models import CompanyUser

router = APIRouter(prefix="/company", tags=["기업 회원"])  # URL 앞 부분


# 회원가입
@router.post(
    "/register",
    summary="기업 회원 가입",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[CompanyUserRegisterResponse],
    responses={
        201: {"description": "회원가입 성공"},
        400: {"description": "비밀번호 불일치"},
        500: {"description": "서버 에러"},
    },
)
async def register_companyuser(
    payload: CompanyUserRegisterRequest, db: AsyncSession = Depends(get_db_session)
):
    company_user = await register_company_user(db, payload)
    user_data = CompanyUserRegisterResponse(
        company_user_id=company_user.id,
        email=company_user.email,
        company_name=company_user.company_name,
    )
    return success_response("회원가입이 완료 되었습니다.", data=user_data)


# 회원가입시 이메일 중복 확인
@router.get(
    "/register/check-email",
    summary="이메일 중복 체크",
    response_model=SuccessResponse[dict],
    responses={409: {"description": "이미 사용 중인 이메일"}},
)
async def check_companyuser_email(
    email: str,
    db: AsyncSession = Depends(get_db_session),
):
    await check_dupl_email(db, email)
    return success_response("사용 가능한 이메일 입니다.", data={"email": email})


# 회원가입시 사업자번호 중복 확인
@router.get(
    "/register/check-brn",
    summary="사업자등록번호 중복 체크",
    response_model=SuccessResponse[dict],
    responses={409: {"description": "이미 등록된 사업자등록번호"}},
)
async def check_companyuser_brn(
    business_reg_number: str,
    db: AsyncSession = Depends(get_db_session),
):
    await check_dupl_business_number(db, business_reg_number)
    return success_response(
        "사용 가능한 사업자 등록번호입니다.",
        data={"business_reg_number": business_reg_number},
    )


# 로그인
@router.post(
    "/login",
    summary="기업 회원 로그인",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[CompanyUserLoginResponse],
    responses={
        200: {"description": "로그인 성공"},
        401: {"description": "이메일 또는 비밀번호 오류"},
        404: {"description": "존재하지 않는 계정"},
    },
)
async def login_companyuser(
    payload: CompanyUserLoginRequest, db: AsyncSession = Depends(get_db_session)
):
    user = await login_company_user(db, payload.email, payload.password)
    access_token = await create_access_token(data={"sub": user.email})
    refresh_token = await create_refresh_token(data={"sub": user.email})

    login_response = CompanyUserLoginResponse(
        company_user_id=user.id,
        email=user.email,
        company_name=user.company.company_name,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    return success_response("로그인이 완료되었습니다.", data=login_response)


# 로그아웃
@router.post(
    "/logout",
    summary="기업 회원 로그아웃",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[None],
    responses={
        200: {"description": "로그아웃 성공"},
    },
)
async def logout_company_user():
    return success_response("로그아웃 되었습니다.")


# 기업 회원 정보 조회 (마이페이지)
@router.get(
    "/me",
    summary="기업 회원 마이페이지",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[CompanyUserInfo],
    responses={
        200: {"description": "조회 성공"},
        403: {"description": "접근 권한 없음"},
        404: {"description": "기업 정보를 찾을 수 없음"},
    },
)
async def get_companyuser(
    db: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
):
    user_data = await get_company_user_mypage(db, current_user)

    return success_response("기업 회원 정보 조회가 완료되었습니다.", data=user_data)


# 기업 정보 수정
@router.patch(
    "/me",
    summary="기업 회원 정보 수정",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[CompanyUserUpdateResponse],
    responses={
        200: {"description": "수정 성공"},
        400: {"description": "비밀번호 불일치"},
        403: {"description": "수정 권한 없음"},
    },
)
async def update_companyuser(
    payload: CompanyUserUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
):
    update_data = await update_company_user(
        db=db, payload=payload, current_user=current_user
    )

    return success_response("기업 회원 정보 수정이 완료되었습니다.", data=update_data)


# 기업 회원 탈퇴
@router.delete(
    "/me",
    summary="기업 회원 탈퇴",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[dict],
    responses={
        200: {"description": "회원 탈퇴 성공"},
        403: {"description": "탈퇴 권한 없음"},
    },
)
async def delete_companyuser(
    current_company_user: CompanyUser = Depends(get_current_company_user),
    db: AsyncSession = Depends(get_db_session),
):
    result = await delete_company_user(db=db, current_user=current_company_user)
    return success_response("회원 탈퇴가 완료되었습니다.", data=result)


# 기업 회원 이메일 찾기
@router.post(
    "/find-email",
    summary="기업 회원 이메일 찾기",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[dict],
    responses={
        200: {"description": "이메일 조회 성공"},
        404: {"description": "일치하는 회원 없음"},
    },
)
async def find_email_companyuser(
    payload: FindCompanyUserEmail,
    db: AsyncSession = Depends(get_db_session),
):
    result = await find_company_user_email(db=db, payload=payload)
    return success_response("이메일이 조회되었습니다.", data=result)


# 1) 재설정용 검증 토큰 발급
@router.post(
    "/reset-password/verify",
    summary="비밀번호 재설정용 토큰 발급",
    response_model=SuccessResponse[PasswordResetVerifyResponse],
    responses={404: {"description": "검증 실패"}},
)
async def verify_reset_password(
    payload: PasswordResetVerifyRequest,
    db: AsyncSession = Depends(get_db_session),
):
    token = await generate_password_reset_token(db, payload)
    return success_response(
        "재설정 토큰이 발급되었습니다.",
        data={"reset_token": token},
    )


# 2) 토큰으로 실제 비밀번호 재설정
@router.post(
    "/reset-password",
    summary="비밀번호 재설정",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[None],
    responses={
        400: {"description": "비밀번호 불일치"},
        401: {"description": "토큰 오류"},
        404: {"description": "사용자 없음"},
    },
)
async def reset_password(
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_db_session),
):
    await reset_password_with_token(
        db, payload.reset_token, payload.new_password, payload.confirm_password
    )
    return success_response("비밀번호가 성공적으로 재설정되었습니다.")


# 기업 회원 토큰 재발급
@router.post(
    "/auth/refresh-token",
    summary="기업 회원 토큰 재발급",
    response_model=SuccessResponse[dict],
)
async def refresh_token_companyuser(
    token_data: CompanyTokenRefreshRequest, db: AsyncSession = Depends(get_db_session)
):
    result = await refresh_company_user_access_token(db=db, token_data=token_data)
    return success_response("토큰 재발급이 완료되었습니다.", data=result)
