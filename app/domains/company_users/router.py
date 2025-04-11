from fastapi import APIRouter

router = APIRouter(
    prefix="/company", # URL 앞 부분
    tags=["Company"]
)

