from app.domains.company_users.schemas import CompanyUserRequest
from app.domains.company_users.utils import check_business_number_valid
from app.models import CompanyInfo, CompanyUser
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# 사업자 등록번호 중복 확인
async def check_dupl_business_number(db:AsyncSession,business_reg_number : str):
    result = await db.execute(select(CompanyInfo).filter_by(business_reg_number=business_reg_number))
    company_reg_no = result.scalars().first()
    if company_reg_no:
        raise HTTPException(
            status_code=400,
            detail={"error": "DuplicateBusinessNumber", "message": "이미 등록된 사업자등록번호입니다."}
        )
# 이메일 중복 확인
async def check_dupl_email(db:AsyncSession,email : str):
    result = await db.execute(select(CompanyUser).filter_by(email=email))
    company_user_email = result.scalars().first()
    if company_user_email:
        raise HTTPException(
            status_code=400,
            detail={"error": "DuplicateEmail", "message": "이미 가입된 이메일입니다."}
        )

# 회원가입 정보 확인
async def register_company_user(db:AsyncSession,payload:CompanyUserRequest):
    # 국세청 진위확인 호출
    if not await check_business_number_valid(
            payload.business_reg_number,
            payload.opening_date.strftime("%Y%m%d"),
            payload.ceo_name
    ):
        raise HTTPException(
            status_code=400,
            detail={"error": "InvalidBusinessNumber", "message": "유효하지 않은 사업자등록번호입니다."}
        )

    # 중복 확인
    await check_dupl_email(db,payload.email)
    await check_dupl_business_number(db,payload.business_reg_number)

    # 정보 저장
    try:
        # 기업 정보 저장
        company_info = await create_company_info(db,payload)
        # 기업 유저(담당자) 정보 저장
        company_user = await create_company_user(db,payload,company_info.id)

        return company_user

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"error": "InternalServerError", "message": "회원가입 처리 중 오류가 발생했습니다."}
        )
# 기업 정보 저장
async def create_company_info(db:AsyncSession,payload:CompanyUserRequest):
    company_info = CompanyInfo(
        company_name=payload.company_name,
        ceo_name=payload.ceo_name,
        business_reg_number=payload.business_reg_number,
        opening_date=payload.opening_date,
        company_intro=payload.company_intro
    )
    db.add(company_info)
    await db.flush() # 임시 저장 (ID 생성을 위해)
    return company_info

# 기업 유저 저장 (담당자)
async def create_company_user(db:AsyncSession,payload:CompanyUserRequest, company_id:int):
    company_user = CompanyUser(
        email=payload.email,
        password=payload.password,
        company_id = company_id,
        manager_name=payload.manager_name,
        manager_phone=payload.manager_phone,
        manager_email=payload.manager_email,
    )

    db.add(company_user)
    await db.commit()
    await db.refresh(company_user)
    return company_user

