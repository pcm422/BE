from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company_users.schemas import (CompanyUserRequest,
                                               CompanyUserUpdateRequest)
from app.domains.company_users.utiles import (check_business_number_valid,
                                              hash_password, verify_password)
from app.domains.users.service import create_access_token, create_refresh_token
from app.models import CompanyInfo, CompanyUser

# 공통 응답 포맷 함수
def success_response(message: str, data):
    return {
        "status": "success",
        "message": message,
        "data": data,
    }

# 사업자 등록번호 중복 확인
async def check_dupl_business_number(db: AsyncSession, business_reg_number: str):
    result = await db.execute(
        select(CompanyInfo).filter_by(business_reg_number=business_reg_number)
    )
    company_reg_no = result.scalars().first()
    if company_reg_no:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"이미 등록된 사업자등록번호입니다."},
        )


# 이메일 중복 확인
async def check_dupl_email(db: AsyncSession, email: str):
    result = await db.execute(select(CompanyUser).filter_by(email=email))
    company_user_email = result.scalars().first()
    if company_user_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"이미 가입된 이메일입니다."},
        )


# 기업 정보 저장
async def create_company_info(db: AsyncSession, payload: CompanyUserRequest):
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


# 기업 유저 저장
async def create_company_user(
    db: AsyncSession, payload: CompanyUserRequest, company_id: int
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


# 회원가입
async def register_company_user(db: AsyncSession, payload: CompanyUserRequest):
    # 국세청 진위확인 호출
    await check_business_number_valid(
        payload.business_reg_number,
        payload.opening_date.strftime("%Y%m%d"),
        payload.ceo_name,
    )

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
    email_result = await db.execute(select(CompanyUser).filter_by(email=email))
    company_user = email_result.scalars().first()

    # 유효값 검증
    if not company_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="가입되지 않은 이메일입니다."
        )
    if not verify_password(password, company_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 올바르지 않습니다.",
        )
    access_token = await create_access_token(data={"sub": company_user.id})
    refresh_token = await create_refresh_token(data={"sub": company_user.id})

    return {
        "company_user": company_user,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


# 기업 회원 정보 조회(마이페이지)
async def get_company_user_mypage(
    db: AsyncSession, company_user_id: int, current_user: CompanyUser
):
    if current_user.id != company_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다."
        )
    if not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 기업 정보를 찾을 수 없습니다.",
        )
    return {
        "company_info": {
            "company_user": current_user.company.company_name,  # 기업이름
            "manager_name": current_user.manager_name,  # 담당자이름
            "manager_email": current_user.manager_email,  # 담당자이메일
            "manager_phone": current_user.manager_phone,  # 담당자 전화번호
            "company_intro": current_user.company.company_intro,  # 기업소개
        },
        "jop_postings": [  # 등록된 공고리스트
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


# 기업 회원 정보수정
async def update_company_user(
    db: AsyncSession,
    company_user_id: int,
    payload: CompanyUserUpdateRequest,
    current_user: CompanyUser,
):
    if current_user.id != company_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="수정 권한이 없습니다."
        )

    # 기업 정보 수정
    if payload.company_intro:
        current_user.company_intro = payload.company_intro
    if payload.address:
        current_user.address = payload.address
    # 담당자 정보 수정
    if payload.manager_phone:
        current_user.manager_phone = payload.manager_phone
    if payload.manager_email:
        current_user.manager_email = payload.manager_email
    if payload.manager_name:
        current_user.manager_name = payload.manager_name

    await db.commit()
    await db.refresh(current_user)
    return current_user

# 기업 회원 탈퇴
async def delete_company_user(db: AsyncSession, company_user_id: int,current_user: CompanyUser):

    if current_user.id != company_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다."
        )
    user = await db.get(CompanyUser, company_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="회원 정보가 없습니다."
        )
    if company_user_id:
        await db.delete(
            select(CompanyUser).filter_by(id=company_user_id)
        )
    return {
        "status": "success",
        "message": "회원 탈퇴가 정상적으로 처리 되었습니다."
    }

