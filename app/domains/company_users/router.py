from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.domains.company_users.schemas import CompanyUserRequest, CompanyUserLoginRequest, BRNValidationRequest
from app.domains.company_users.service import register_company_user, login_company_user
from app.domains.company_users.utiles import check_business_number_valid

router = APIRouter(prefix="/company", tags=["Company Users"])  # URL 앞 부분

# 회원가입
@router.post("/register")
async def register_company_user_router(
        payload: CompanyUserRequest, db:AsyncSession = Depends(get_db_session)
):
    company_user = await register_company_user(db, payload)
    return {
        "status": "success",
        "message": "회원가입이 완료되었습니다.",
        "data": company_user
    }

# 로그인
@router.post("/login")
async def login_company_user_router(
        payload: CompanyUserLoginRequest, db: AsyncSession = Depends(get_db_session)
):
    result = await login_company_user(db, payload)
    return {
        "status": "success",
        "message": "로그인이 완료되었습니다.",
        "data": result
    }

# 사업자 등록번호 확인
@router.post("/validate-brn")
async def validate_brn(payload: BRNValidationRequest):

    try:
        is_valid = await check_business_number_valid(
            business_reg_number=payload.business_reg_number,
            opening_date=payload.opening_date,
            ceo_name=payload.ceo_name
        )
        if is_valid:
            return {
                "status": "success",
                "message" : "사업자등록번호가 인증되었습니다."
            }
        else:
            raise HTTPException(status_code=409, detail="등록되지 않은 사업자등록번호입니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))