from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.utils import create_access_token
from app.domains.company_users.schemas import (CompanyUserBase,
                                               CompanyUserRegisterRequest,
                                               CompanyUserUpdateRequest,
                                               FindCompanyUserEmail,
                                               JobPostingsSummary,
                                               ResetCompanyUserPassword, CompanyTokenRefreshRequest)
from app.domains.company_users.utiles import (check_password_match,
                                              hash_password, verify_password, decode_refresh_token, success_response)
from app.models import CompanyInfo, CompanyUser


# 사업자 등록번호 중복 확인
async def check_dupl_business_number(db: AsyncSession, business_reg_number: str):
    result = await db.execute(
        select(CompanyInfo).filter_by(business_reg_number=business_reg_number)
    )
    company_reg_no = result.scalars().first()
    if company_reg_no:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 사업자등록번호입니다.",
        )


# 이메일 중복 확인
async def check_dupl_email(db: AsyncSession, email: str):
    result = await db.execute(select(CompanyUser).filter_by(email=email))
    email = result.scalars().first()
    if email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 가입된 이메일입니다.",
        )


# 기업 정보 저장
async def create_company_info(db: AsyncSession, payload: CompanyUserBase):
    company_info = CompanyInfo(
        company_name=payload.company_name,
        manager_name=payload.manager_name,
        manager_phone=payload.manager_phone,
        manager_email=str(payload.manager_email),
        ceo_name=payload.ceo_name,
        business_reg_number=payload.business_reg_number,
        opening_date=payload.opening_date,
        company_intro=payload.company_intro,
    )
    db.add(company_info)
    await db.flush()  # 임시 저장 (ID 생성을 위해)
    return company_info


# 기업 회원 저장
async def create_company_user(
    db: AsyncSession, payload: CompanyUserBase, company_id: int
) -> CompanyUser:
    company_user = CompanyUser(
        email=str(payload.email),
        password=hash_password(payload.password),
        company_id=company_id,
    )
    db.add(company_user)
    await db.commit()
    await db.refresh(company_user)
    return company_user


# 기업 회원 가입
async def register_company_user(db: AsyncSession, payload: CompanyUserRegisterRequest):
    # 비밀번호 일치 확인
    check_password_match(payload.password, payload.confirm_password)
    # 중복 확인
    await check_dupl_email(db, str(payload.email))
    await check_dupl_business_number(db, payload.business_reg_number)

    # 정보 저장
    try:
        # 기업 정보 저장
        company_info = await create_company_info(db, payload)
        # 기업 유저 정보 저장
        company_user = await create_company_user(db, payload, company_info.id)

        return company_user

    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 처리 중 오류가 발생했습니다.",
        )


# 기업 회원 로그인
async def login_company_user(db: AsyncSession, email: str, password: str):
    result = await db.execute(select(CompanyUser).filter_by(email=email))
    company_user = result.scalars().first()

    # 유효값 검증
    if not company_user:
        raise HTTPException(404, detail="가입되지 않은 이메일입니다.")
    if not verify_password(password, company_user.password):
        raise HTTPException(
            status_code=401,
            detail="비밀번호가 일치하지 않습니다.",
        )
    return company_user


# 기업 회원 마이페이지 조회
async def get_company_user_mypage(db: AsyncSession, current_user: CompanyUser):

    result = await db.execute(
        select(CompanyUser)
        .options(
            selectinload(CompanyUser.company), selectinload(CompanyUser.job_postings)
        )
        .where(CompanyUser.id == current_user.id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기업 회원 정보를 찾을 수 없습니다.",
        )
    company = user.company
    data = {
        "company_user_id": user.id,
        "email": user.email,
        "company_name": company.company_name,
        "company_id": company.id,
        "manager_name": company.manager_name,
        "manager_email": company.manager_email,
        "manager_phone": company.manager_phone,
        "company_intro": company.company_intro,
        "business_reg_number": company.business_reg_number,
        "opening_date": company.opening_date,
        "ceo_name": company.ceo_name,
        "address": company.address,
        "company_image": company.company_image,
        "job_postings": [
            JobPostingsSummary.from_orm(jp).dict() for jp in user.job_postings
        ],
    }
    return data


# 기업 회원 정보 수정
async def update_company_user(
    db: AsyncSession, payload: CompanyUserUpdateRequest, current_user: CompanyUser
):
    has_changes = False

    # 비밀번호 수정
    if payload.password:
        check_password_match(payload.password, payload.confirm_password)
        if not verify_password(payload.password, current_user.password):
            current_user.password = hash_password(payload.password)
            has_changes = True

    company = current_user.company
    # 수정할 유저 필드
    user_fields = {
        "manager_name": payload.manager_name,
        "manager_phone": payload.manager_phone,
        "manager_email": payload.manager_email,
        "company_intro": payload.company_intro,
        "address": payload.address,
        "company_image": payload.company_image,
    }

    for field, new_value in user_fields.items():
        if new_value is not None and getattr(company, field) != new_value:
            setattr(company, field, new_value)
            has_changes = True

    # 커밋 처리
    if has_changes:
        await db.commit()
        await db.refresh(company)

    result = {
        "company_user_id": current_user.id,
        "email": current_user.email,
        "company_name": company.company_name,
        "manager_name": company.manager_name,
        "manager_email": company.manager_email,
        "manager_phone": company.manager_phone,
        "company_intro": company.company_intro,
        "address": company.address,
        "company_image": company.company_image,
    }
    return result


# 기업 회원 탈퇴
async def delete_company_user(db: AsyncSession, current_user: CompanyUser):
    company_info = current_user.company
    await db.delete(current_user)
    if company_info:
        await db.delete(company_info)  # 기업 정보도 삭제
    await db.commit()

    deleted_company_user = {
        "company_user_id": current_user.id,
        "company_name": company_info.company_name,
    }
    return deleted_company_user


# 기업 회원 이메일 찾기
async def find_company_user_email(db: AsyncSession, payload: FindCompanyUserEmail):
    result = await db.execute(
        select(CompanyUser)
        .join(CompanyInfo)
        .where(
            CompanyInfo.ceo_name == payload.ceo_name,
            CompanyInfo.opening_date == payload.opening_date,
            CompanyInfo.business_reg_number == payload.business_reg_number,
            CompanyUser.company_id == CompanyInfo.id,
        )
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="일치하는 기업 회원을 찾을 수 없습니다.",
        )
    return {"company_name": user.company.company_name, "email": user.email}


# 기업회원 비밀번호 재설정
async def reset_company_user_password(
    db: AsyncSession, payload: ResetCompanyUserPassword
):
    result = await db.execute(
        select(CompanyUser)
        .join(CompanyInfo)
        .where(
            CompanyInfo.ceo_name == payload.ceo_name,
            CompanyInfo.opening_date == payload.opening_date,
            CompanyInfo.business_reg_number == payload.business_reg_number,
            CompanyUser.email == payload.email,
            CompanyUser.company_id == CompanyInfo.id,
        )
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="해당 회원을 찾을 수 없습니다.",
        )

    check_password_match(
        payload.new_password, payload.confirm_password
    )  # 비밀번호 인증
    user.password = hash_password(payload.new_password)

    await db.commit()
    await db.refresh(user)

    return user.email

# 리프레쉬 토큰 생성
async def refresh_company_user_access_token(
        db:AsyncSession, token_data:CompanyTokenRefreshRequest):
    payload = decode_refresh_token(token_data.refresh_token)
    email:str = payload.get("sub")

    result = await db.execute(select(CompanyUser).filter_by(email=email))
    user=result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기업 회원을 찾을 수 없습니다."
        )
    new_access_token = await create_access_token(
        data={"sub": user.email})

    return new_access_token