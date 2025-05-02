import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from app.admin.admin import setup_admin
from app.core.config import ENVIRONMENT
from app.core.scheduler import start_scheduler
from app.domains.favorites.router import router as favorites_router
from app.domains.job_postings.router import router as job_postings_router
from app.domains.users.oauth.social_router import router as social_router
from app.domains.users.router import router as users_router
from app.domains.company_users.router import router as company_users_router
from app.domains.company_info.router import router as company_info_router
from app.domains.resumes.router import router as resumes_router
from app.domains.job_applications.router import router as applications_router

# FastAPI 애플리케이션 인스턴스 생성 (프로젝트 제목 및 버전 설정)
app = FastAPI(title="My FastAPI Project", version="0.1.0")

# Add CORS middleware
origins = [
    "http://localhost:5173",
    "https://dev.toseniors.r-e.kr",
    "https://toseniors.r-e.kr"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # 쿠키를 포함한 요청 허용
    allow_methods=["*"], # 모든 HTTP 메소드 허용
    allow_headers=["*"], # 모든 HTTP 헤더 허용
)

setup_admin(app)

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


app.include_router(users_router)
app.include_router(job_postings_router)
app.include_router(favorites_router)
app.include_router(social_router)

app.include_router(company_users_router)
app.include_router(company_info_router)
app.include_router(resumes_router)
app.include_router(applications_router)

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = "upgrade-insecure-requests"
        return response

app.add_middleware(CSPMiddleware)