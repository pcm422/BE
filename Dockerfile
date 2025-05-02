FROM python:3.12-slim

# 시스템 패키지 업데이트 및 필요 도구 설치 (PostgreSQL 클라이언트 등)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc default-libmysqlclient-dev build-essential \
    # 필요에 따라 PostgreSQL 클라이언트 추가 (psql 명령어 사용 시)
    postgresql-client \
    # Supervisor 설치 추가
    supervisor \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Poetry 설치
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 -

# Poetry 설정: 가상 환경 생성 비활성화 (이미 위에서 .toml에 설정했으면 없어도 무방)
RUN poetry config virtualenvs.create false

WORKDIR /app

# 의존성 설치 (코드 복사 전에 실행하여 Docker 빌드 캐시 활용)
COPY pyproject.toml poetry.lock* /app/
# --no-root: 프로젝트 자체는 설치하지 않음 (볼륨 마운트 사용)
# --sync: pyproject.toml에 명시되지 않은 패키지는 제거
RUN poetry install --no-root --sync

# Supervisor 설정 파일 복사
# 프로젝트 루트에 supervisord.conf 파일이 있다고 가정
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 스케줄러 실행 스크립트 복사
COPY run_scheduler.py /app/run_scheduler.py

# 나머지 애플리케이션 코드 복사 (로컬에서는 볼륨 마운트로 덮어쓰지만, 빌드 이미지에는 포함)
COPY ./app /app/app
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini

# 기본 실행 명령을 supervisord로 변경
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]