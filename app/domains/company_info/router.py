from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.domains.company_info.schemas import PublicCompanyInfo
from app.domains.company_info.service import get_company_info
from app.domains.company_users.schemas import SuccessResponse
from app.domains.company_users.utiles import success_response

router = APIRouter(prefix="/companies", tags=["company_info"])


@router.get(
    "/{company_id}",
    summary="기업 정보 조회",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[PublicCompanyInfo],
    responses={404: {"description": "기업 정보를 찾을 수 없음"}},
)
async def get_companyinfo(company_id: int, db: AsyncSession = Depends(get_db_session)):
    """
    누구나 볼 수 있는 기업 정보 페이지 입니다.
    """
    info = await get_company_info(db, company_id)
    return success_response("기업 정보 조회 성공", data=info)
