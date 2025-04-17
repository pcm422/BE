from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company_users.schemas import (
    CompanyUserBase,
    CompanyUserUpdateRequest,
    FindCompanyUserEmail,
    ResetCompanyUserPassword,
)
from app.domains.company_users.utiles import (
    check_business_number_valid,
    check_password_match,
    hash_password,
    verify_password,
)
from app.domains.users.service import create_access_token, create_refresh_token
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
    company_user_email = result.scalars().first()
    if company_user_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 가입된 이메일입니다.",
        )


# 기업 정보 저장
async def create_company_info(db: AsyncSession, payload: CompanyUserBase):
    company_info = CompanyInfo(
        company_name=payload.company_name,
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
        manager_name=payload.manager_name,
        manager_phone=payload.manager_phone,
        manager_email=str(payload.manager_email),
    )
    db.add(company_user)
    await db.commit()
    await db.refresh(company_user)
    return company_user


# 기업 회원 가입
async def register_company_user(db: AsyncSession, payload: CompanyUserBase):
    # 국세청 진위확인 호출
    await check_business_number_valid(
        payload.business_reg_number,
        payload.opening_date.strftime("%Y%m%d"),
        payload.ceo_name,
    )

    # 비밀번호 일치 확인
    check_password_match(payload.password, payload.confirm_password)
    # 중복 확인
    await check_dupl_email(db, str(payload.email))
    await check_dupl_business_number(db, payload.business_reg_number)

    # 정보 저장
    try:
        # 기업 정보 저장
        company_info = await create_company_info(db, payload)
        # 기업 유저(담당자) 정보 저장
        company_user = await create_company_user(db, payload, company_info.id)

        return company_user

    except Exception as e:
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
async def get_company_user_mypage(
    db: AsyncSession, company_user_id: int, current_user: CompanyUser
):
    if current_user.id or current_user != company_user_id:
        raise HTTPException(403, detail="접근 권한이 없습니다.")
    if not current_user.id:
        raise HTTPException(
            status_code=404,
            detail="해당 기업 정보를 찾을 수 없습니다.",
        )

    result = {
        "company_user_id": current_user.id,  # 기업 회원 고유 ID
        "email": current_user.email,  # 기업 계정 이메일
        "manager_name": current_user.manager_name,  # 담당자이름
        "manager_email": current_user.manager_email,  # 담당자이메일
        "manager_phone": current_user.manager_phone,  # 담당자 전화번호
        "company": {
            "company_name": current_user.company.company_name,  # 기업이름
            "company_intro": current_user.company.company_intro,  # 기업소개
            "business_reg_number": current_user.company.business_reg_number,
            "opening_date": current_user.company.opening_date.isoformat(),
            "ceo_name": current_user.company.ceo_name,
        },
        # 공고 리스트
        "jop_postings": [
            {
                "id": job_posting.id,
                "title": job_posting.title,
                "work_address": job_posting.work_address,
                "deadline_at": job_posting.deadline_at,
                "is_always_recruiting": job_posting.is_always_recruiting,
            }
            for job_posting in current_user.job_postings
        ],
    }
    return result


# 기업 회원 정보 수정
async def update_company_user(
    db: AsyncSession,
    company_user_id: int,
    payload: CompanyUserUpdateRequest,
    current_user: CompanyUser,
):
    # 수정 권한 체크
    if current_user.id != company_user_id:
        raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")

    has_changes = False

    # 수정할 유저 필드
    user_fields = {
        "manager_name": payload.manager_name,
        "manager_phone": payload.manager_phone,
        "manager_email": payload.manager_email,
    }

    # 수정할 기업 필드
    company_fields = {
        "company_intro": payload.company_intro,
        "address": payload.address,
        "company_image": payload.company_image,
    }

    # 담당자 정보 수정
    for field, value in user_fields.items():
        if value is not None and getattr(current_user, field) != value:
            setattr(current_user, field, value)
            has_changes = True

    # 기업 정보 수정
    for field, value in company_fields.items():
        if value is not None and getattr(current_user.company, field) != value:
            setattr(current_user.company, field, value)
            has_changes = True

    # 비밀번호 수정
    if payload.password:
        check_password_match(payload.password, payload.confirm_password)
        if not verify_password(payload.password, current_user.password):
            current_user.password = hash_password(payload.password)
            has_changes = True

    # 커밋 처리
    if has_changes:
        await db.commit()
        await db.refresh(current_user)

    result = {
        "company_user_id": current_user.id,
        "email": current_user.email,
        "manager_name": current_user.manager_name,
        "manager_phone": current_user.manager_phone,
        "manager_email": current_user.manager_email,
        "company": {
            "company_name": current_user.company.company_name,
            "company_intro": current_user.company.company_intro,
            "business_reg_number": current_user.company.business_reg_number,
            "opening_date": current_user.company.opening_date,
            "ceo_name": current_user.company.ceo_name,
            "address": current_user.company.address,
            "company_image": current_user.company.company_image,
        },
    }
    return result


# 기업 회원 탈퇴
async def delete_company_user(
    db: AsyncSession, company_user_id: int, current_user: CompanyUser
):
    if not current_user.id:
        raise HTTPException(status_code=404, detail="회원 정보가 없습니다.")
    if current_user.id != company_user_id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    company_info = current_user.company
    await db.delete(current_user)
    if company_info:
        await db.delete(company_info)  # 기업 정보도 삭제
    await db.commit()

    deleted_company_user = {
        "company_user_id": company_user_id,
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
