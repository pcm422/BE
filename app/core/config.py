import os

from dotenv import load_dotenv  # .env 파일 로드 지원

load_dotenv()

# 데이터베이스 연결 URL
DATABASE_URL = os.getenv("DATABASE_URL")

# 애플리케이션 시크릿 키 (JWT 토큰 서명 등에 사용)
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key_for_safety")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES"))

# 현재 실행 환경 구분용 변수
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

# 국세청 api 키
BRN_API_KEY = os.getenv("BRN_API_KEY")

# 이메일 전송 관련 환경 변수
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.naver.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "465"))
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    raise ValueError("SMTP 인증 정보가 설정되지 않았습니다.")

# 이메일 인증/비밀번호 재설정 링크에서 사용할 사이트 URL
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")
