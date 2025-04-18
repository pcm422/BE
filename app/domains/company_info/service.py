from fastapi import HTTPException ,status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company_info.schemas import PublicCompanyInfo
from app.domains.company_users.schemas import JobPostingsSummary
from app.models import CompanyInfo
from sqlalchemy import select

async def get_company_info(db: AsyncSession,
                           company_id: int)-> PublicCompanyInfo:

    result = await db.execute(
        select(CompanyInfo).where(CompanyInfo.id == company_id)
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="기업 정보를 찾을 수 없습니다.")

    postings = [
        JobPostingsSummary.from_orm(jp)
        for jp in company.job_postings
    ]

    return PublicCompanyInfo(
        company_id=company.id,
        company_name=company.company_name,
        company_intro=company.company_intro,
        business_reg_number=company.business_reg_number,
        manager_name=company.company_users.manager_name,
        manager_email=company.company_users.manager_email,
        manager_phone=company.company_users.manager_phone,
        opening_date=company.opening_date,
        ceo_name=company.ceo_name,
        address=company.address,
        company_image=company.company_image,
        job_postings=postings,
    )