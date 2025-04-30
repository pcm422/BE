import logging  # 기본 로깅 모듈
from logging.handlers import TimedRotatingFileHandler  # 시간 기반 로그 분할 핸들러
import os

# 로그 디렉토리 경로 설정
LOG_DIR = "logs"
LOG_FILE = "app.log"
LOG_PATH = os.path.join(LOG_DIR, LOG_FILE)

# 로그 디렉토리가 없다면 생성
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 로깅 포맷 설정
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 루트 로거 설정
logger = logging.getLogger()  # 루트 로거 사용
logger.setLevel(logging.INFO)  # 전체 로그 레벨 설정

# 핸들러 중복 등록 방지
if not logger.handlers:
    # 파일 핸들러: 자정마다 새로운 로그 파일, 최대 7일 보관
    file_handler = TimedRotatingFileHandler(
        filename=LOG_PATH, when="midnight", interval=1, backupCount=7, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(file_handler)

    # 콘솔 핸들러 추가 (옵션)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(console_handler)