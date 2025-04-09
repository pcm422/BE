import os
from dotenv import load_dotenv # .env 파일 로드 지원

# 데이터베이스 연결 URL
DATABASE_URL = os.getenv("DATABASE_URL")

# 애플리케이션 시크릿 키 (JWT 토큰 서명 등에 사용)
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key_for_safety")

# 현재 실행 환경 구분용 변수 
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")