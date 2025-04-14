from fastapi import FastAPI
from app.domains.users.router import router as users_router
from app.domains.job_postings.router import router as job_postings_router
from app.core.config import ENVIRONMENT
from fastapi import FastAPI, Security
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.domains.company_users.router import router as company_users_router
# FastAPI 애플리케이션 인스턴스 생성 (프로젝트 제목 및 버전 설정)
app = FastAPI(title="My FastAPI Project", version="0.1.0")

bearer_scheme = HTTPBearer()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="My API",
        version="1.0.0",
        description="API with Bearer token only",
        routes=app.routes,
    )
    # securitySchemes 수동 정의
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
        }
    }
    # 전체 API에 Bearer를 기본 적용하고 싶으면 아래와 같이 설정
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
@app.get("/")
async def root():
    return {"message": f"Hello World in {ENVIRONMENT} environment"}

# 사용자 도메인 라우터를 애플리케이션에 포함
# prefix: 해당 라우터의 모든 경로 앞에 "/api/users" 추가
# tags: API 문서에서 해당 라우터의 경로들을 "users" 그룹으로 묶음
app.include_router(users_router)
app.include_router(job_postings_router)
app.include_router(company_users_router)