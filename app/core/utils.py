import bcrypt

from app.models.company_users import CompanyUser


# 임시 인증된 유저 반환 (JWT 없이)
async def get_current_company_user() -> CompanyUser:
    # 실제론 여기서 JWT 디코딩 및 DB 조회가 들어가야 함
    return CompanyUser(id=1, company_id=1)  # 테스트용 더미 객체


def hash_password(password: str) -> str:
    """비밀번호를 bcrypt 해시로 변환"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """입력한 비밀번호와 해시가 일치하는지 확인"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )
