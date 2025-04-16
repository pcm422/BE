from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.utils import get_current_company_user
from app.domains.company_users.schemas import (BRNValidationRequest,
                                               CompanyUserLoginRequest,
                                               CompanyUserRequest,
                                               CompanyUserUpdateRequest, FindCompanyUserEmail, ResetCompanyUserPassword)
from app.domains.company_users.service import (get_company_user_mypage,
                                               login_company_user,
                                               register_company_user,
                                               success_response,
                                               update_company_user, find_company_user_email,
                                               reset_company_user_password, delete_company_user)
from app.domains.company_users.utiles import check_business_number_valid
from app.models import CompanyUser

router = APIRouter(prefix="/company", tags=["Company Users"])  # URL 앞 부분


# 회원가입
@router.post("/register")
async def register_companyuser(
    payload: CompanyUserRequest, db: AsyncSession = Depends(get_db_session)
):
    result = await register_company_user(db, payload)
    return result


# 로그인
@router.post("/login")
async def login_companyuser(
    payload: CompanyUserLoginRequest, db: AsyncSession = Depends(get_db_session)
):
    data = await login_company_user(db, payload.email, payload.password)
    return data


# 로그아웃
@router.post("/logout")
async def logout_companyuser():
    return {"status": "success", "message": "로그아웃 되었습니다."}


# 사업자 등록번호 확인
@router.post("/validate-brn")
async def validate_brn(payload: BRNValidationRequest):

    try:
        is_valid = await check_business_number_valid(
            business_reg_number=payload.business_reg_number,
            opening_date=payload.opening_date,
            ceo_name=payload.ceo_name,
        )
        if is_valid:
            return success_response("사업자등록번호가 인증되었습니다.", is_valid)
        else:
            raise HTTPException(
                status_code=409, detail="등록되지 않은 사업자등록번호입니다."
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 기업 회원 정보 조회 (마이페이지)
@router.get("/me")
async def get_companyuser(
    db: AsyncSession = Depends(get_db_session),
    current_company_user: CompanyUser = Depends(get_current_company_user),
):
    data = await get_company_user_mypage(
        db=db,
        company_user_id=current_company_user.id,
        current_user=current_company_user,
    )
    return data


# 기업 정보 수정
@router.patch("/{company_user_id}")
async def update_companyuser(
    payload: CompanyUserUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_company_user: CompanyUser = Depends(get_current_company_user),
):
    update_data = await update_company_user(
        db=db,
        payload=payload,
        current_user=current_company_user,
        company_user_id=current_company_user.id,
    )
    return update_data


# 기업 회원 탈퇴
@router.delete("/{company_user_id}")
async def delete_companyuser(
    company_user_id: int,
    current_company_user: CompanyUser = Depends(get_current_company_user),
    db: AsyncSession = Depends(get_db_session),
):
    result = await delete_company_user(
        db=db, company_user_id=company_user_id, current_user=current_company_user
    )
    return result


# 기업 회원 아이디 찾기
@router.post("/find-email")
async def find_email_companyuser(
    payload: FindCompanyUserEmail,
    db: AsyncSession = Depends(get_db_session),
):
    return await find_company_user_email(db=db, payload=payload)

# 기업 회원 비밀번호 재설정
@router.post("/reset-password")
async def reset_password_companyuser(
        payload: ResetCompanyUserPassword,
        db: AsyncSession = Depends(get_db_session),
):
    return await reset_company_user_password(db=db, payload=payload)