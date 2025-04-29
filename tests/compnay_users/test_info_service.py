import pytest
from fastapi import HTTPException, status

from app.domains.company_info.schemas import PublicCompanyInfo
from app.domains.company_info.service import get_company_info


# 더미 ORM 객체
class DummyCompany:
    def __init__(self, id):
        self.id = id
        self.company_name = "test company"
        self.company_intro = "Introduce the company, Hello word!"
        self.business_reg_number = "1234567890"
        self.opening_date = "20200101"
        self.ceo_name = "CEO"
        self.manager_name = "매니져"
        self.manager_phone = "01011112222"
        self.manager_email = "mgr@c.com"
        self.address = None
        self.company_image = None
        self.job_postings = []  # 빈 리스트


# 더미 결과 객체
class DummyResult:
    def __init__(self, v):
        self._v = v

    def scalars(self):
        return self

    def first(self):
        return self._v


# 더미 세션
class DummySession:
    def __init__(self, result):
        self._result = result

    async def execute(self, query):
        return DummyResult(self._result)


@pytest.mark.asyncio
async def test_get_company_info_success():
    """존재하는 기업이면 PublicCompanyInfo 반환"""
    dummy = DummyCompany(42)
    db = DummySession(dummy)
    info = await get_company_info(db, 42)
    assert isinstance(info, PublicCompanyInfo)
    assert info.company_id == 42
    assert info.company_name == "test company"


@pytest.mark.asyncio
async def test_get_company_info_not_found():
    """기업이 없으면 404 HTTPException"""
    db = DummySession(None)
    with pytest.raises(HTTPException) as exc:
        await get_company_info(db, 99)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert "찾을 수 없습니다" in exc.value.detail
