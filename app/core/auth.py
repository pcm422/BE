from app.models.company_users import CompanyUser

# 임시 인증된 유저 반환 (JWT 없이)
async def get_current_company_user() -> CompanyUser:
    # 실제론 여기서 JWT 디코딩 및 DB 조회가 들어가야 함
    return CompanyUser(id=1, company_id=1)  # 테스트용 더미 객체