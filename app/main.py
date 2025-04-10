from fastapi import FastAPI
from app.domains.users.router import router as users_router
from app.domains.job_postings.router import router as job_postings_router
from app.core.config import ENVIRONMENT

# FastAPI 애플리케이션 인스턴스 생성 (프로젝트 제목 및 버전 설정)
app = FastAPI(title="My FastAPI Project", version="0.1.0")

@app.get("/")
async def root():
    return {"message": f"Hello World in {ENVIRONMENT} environment"}

# 사용자 도메인 라우터를 애플리케이션에 포함
# prefix: 해당 라우터의 모든 경로 앞에 "/api/users" 추가
# tags: API 문서에서 해당 라우터의 경로들을 "users" 그룹으로 묶음
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(job_postings_router)