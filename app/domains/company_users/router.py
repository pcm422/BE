from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.utils import get_current_company_user
from app.domains.company_users.schemas import (
    CompanyUserRequest,
    CompanyUserLoginRequest,
    BRNValidationRequest,
    CompanyUserUpdateRequest,
)
from app.domains.company_users.service import (
    register_company_user,
    login_company_user,
    update_company_user,
)
from app.domains.company_users.utiles import check_business_number_valid
from app.models import CompanyUser

router = APIRouter(prefix="/company", tags=["Company Users"])  # URL 앞 부분


# 회원가입
@router.post("/register")
async def register_companyuser(
    payload: CompanyUserRequest, db: AsyncSession = Depends(get_db_session)
):
    company_user = await register_company_user(db, payload)
    return {
        "status": "success",
        "message": "회원가입이 완료되었습니다.",
        "data": company_user,
    }


# 로그인
@router.post("/login")
async def login_companyuser(
    payload: CompanyUserLoginRequest, db: AsyncSession = Depends(get_db_session)
):
    result = await login_company_user(db, payload.email, payload.password)
    return {
        "status": "success",
        "message": "로그인이 완료되었습니다.",
        "access_token": result["access_token"],
        "token_type": "bearer",
        "data": {
            "company_user": {
                "company_user_id": result["company_user"].id,
                "email": result["company_user"].email,
                "cem_name": result["company_user"].manager_name,
            }
        },
    }


# 로그아웃
@router.post("/logout")
async def logout_company_user():
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
            return {"status": "success", "message": "사업자등록번호가 인증되었습니다."}
        else:
            raise HTTPException(
                status_code=409, detail="등록되지 않은 사업자등록번호입니다."
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 기업 회원 정보 조회 (마이페이지)
@router.get("/me")
async def get_companyuser(
    current_company_user: CompanyUser = Depends(get_current_company_user,),
):
    data = await get_company_user_mypage(current_company_user)
    return {
        "status": "success",
        "message": "기업 회원 정보 조회 성공",
        "data": data,
    }


# 기업 정보 수정
@router.patch("/{company_user_id}")
async def update_companyuser(
    payload: CompanyUserUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
):
    company_user_update = await update_company_user(db, payload, current_user)
    return {
        "status": "success",
        "message": "기업 정보가 수정되었습니다.",
        "data": {
            "company_user_id": company_user_update["company_user_id"],
            "company_intro": company_user_update["company_intro"],
            "address": company_user_update["address"],
            "manager_name": company_user_update["manager_name"],
            "manager_email": company_user_update["manager_email"],
            "manager_phone": company_user_update["manager_phone"],
        },
    }
