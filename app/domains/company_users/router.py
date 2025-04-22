from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.utils import (create_access_token, create_refresh_token,
                            get_current_company_user)
from app.domains.company_users.schemas import (CompanyUserInfo,
                                               CompanyUserLoginRequest,
                                               CompanyUserLoginResponse,
                                               CompanyUserRegisterRequest,
                                               CompanyUserRegisterResponse,
                                               CompanyUserUpdateRequest,
                                               CompanyUserUpdateResponse,
                                               FindCompanyUserEmail,
                                               ResetCompanyUserPassword,
                                               SuccessResponse)
from app.domains.company_users.service import (delete_company_user,
                                               find_company_user_email,
                                               get_company_user_mypage,
                                               login_company_user,
                                               register_company_user,
                                               reset_company_user_password,
                                               update_company_user)
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
        409: {"description": "중복 이메일 또는 중복된 사업자등록번호"},
        500: {"description": "서버 에러"},
        400: {"description": "비밀번호 불일치"},
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


# 기업 회원 비밀번호 재설정
@router.post(
    "/reset-password",
    summary="비밀번호 재설정",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[dict],
    responses={
        200: {"description": "비밀번호 재설정 완료"},
        400: {"description": "비밀번호 불일치"},
        404: {"description": "일치하는 회원 없음"},
    },
)
async def reset_password_companyuser(
    payload: ResetCompanyUserPassword,
    db: AsyncSession = Depends(get_db_session),
):
    result = await reset_company_user_password(db=db, payload=payload)
    return success_response(
        "기업 회원의 비밀번호 재설정이 완료되었습니다.",
        data={"email": result},
    )
