from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db_session
from app.core.utils import upload_image_to_ncp
from app.domains.resumes.schemas import ResumeCreate, ResumeUpdate
from app.domains.resumes.service import (
    serialize_resume,
    get_resume_for_user,
    create_new_resume,
    update_existing_resume,
    delete_resume_by_id
)
from app.domains.users.router import read_current_user
import logging
logger = logging.getLogger(__name__)
router = APIRouter()

# 현재 사용자의 이력서를 조회함
@router.get("/resumes", tags=["이력서"])
async def get_resume(Authorization: str = Header(...), db: AsyncSession = Depends(get_db_session)):
    """
    현재 인증된 사용자의 최신 이력서를 조회한다.
    jwt 토큰을 사용하여 사용자를 식별하고 이력서와 연관된 학력정보를 가져온다.
    """
    # 현재 인증된 사용자 정보를 가져옴
    user = await read_current_user(Authorization=Authorization, db=db)
    # 쿼리 시점에 'selectinload'를 통해 educations 관계를 미리 로드함
    resume = await get_resume_for_user(user.id, db)
    if resume is None:
        raise HTTPException(status_code=404, detail="이력서의 내용을 찾을 수 없습니다.")
    return {"status": "success", "data": serialize_resume(resume)}

# 새로운 이력서를 생성함
@router.post("/resumes", tags=["이력서"])  # HTTP POST 메서드를 라우팅
async def create_resume(
    resume_data: str = Form(
        ...,description=
    '''
    {
      "user_id": 7,
      "resume_image": "",
      "desired_area": "서울",
      "introduction": "자기소개 내용",
      "educations": [
        {
          "education_type": "고등학교",
          "school_name": "서울고등학교",
          "education_status": "졸업",
          "start_date": "2010-03-01T00:00:00",
          "end_date": "2013-02-28T00:00:00"
        },
        {
          "education_type": "대학교(4년)",
          "school_name": "서울대학교",
          "education_status": "졸업",
          "start_date": "2013-03-01T00:00:00",
          "end_date": "2017-02-28T00:00:00"
        }
      ],
      "experiences": [
        {
          "company_name": "넥스트러너스",
          "position": "Backend Developer",
          "start_date": "2020-03-01",
          "end_date": "2023-01-01",
          "description": "백엔드 개발자"
        },
        {
          "company_name": "오즈코딩스쿨",
          "position": "Backend Developer",
          "start_date": "2020-03-01",
          "end_date": "2023-01-01",
          "description": "백엔드 개발자"
        }
      ]
    }
    '''
    ),       # 이력서 + 학력사항을 포함한 JSON 문자열
    file: UploadFile = File(None),              # 이미지 파일 업로드
    Authorization: str = Header(...),           # 인증 토큰
    db: AsyncSession = Depends(get_db_session)   # DB 세션 의존성
):
    """
    새로운 이력서를 생성한다.
    바디에는 이력서 정보와 학력사항 정보를 포함한 정보를 받는다.
    jwt로 사용자를 확인하고 정보에 user_id가 일치해야 한다.
    생성 후 이력서, 학력사항 반환한다.
    """
    # 현재 사용자를 토큰으로부터 조회
    user = await read_current_user(Authorization=Authorization, db=db)
    parsed_data = ResumeCreate.model_validate_json(resume_data)
    # user_id 검증 (JWT 토큰의 사용자와 요청 바디의 user_id가 동일해야 함)
    if parsed_data.user_id != user.id:
        raise HTTPException(status_code=400, detail="사용자 ID가 일치하지 않습니다.")
    if file and file.filename:
        try:
            image_url = await upload_image_to_ncp(file, folder="resumes")
            parsed_data.resume_image = image_url
            logger.info(f"✅ 파일 업로드 성공: {image_url}")
        except Exception as e:
            logger.error(f"❌ 이미지 업로드 실패: {str(e)}")
            raise HTTPException(status_code=400, detail=f"이미지 업로드 실패: {str(e)}")
    else:
        logger.warning("⚠️ file 또는 file.filename이 존재하지 않음")
    new_resume = await create_new_resume(parsed_data, db)
    return {"status": "success", "data": serialize_resume(new_resume)}

# 특정 이력서를 수정함
@router.patch("/resumes/{resumes_id}", tags=["이력서"])  # HTTP PATCH 메서드와 경로 파라미터, 태그 지정
async def update_resume(
    resumes_id: int,  # URL 경로에서 이력서 ID 수신
        resume_data: str = Form(..., description=
        '''
    {
      "user_id": 7,
      "resume_image": "",
      "desired_area": "서울",
      "introduction": "자기소개 내용",
      "educations": [
        {
          "education_type": "고등학교",
          "school_name": "서울고등학교",
          "education_status": "졸업",
          "start_date": "2010-03-01T00:00:00",
          "end_date": "2013-02-28T00:00:00"
        },
        {
          "education_type": "대학교(4년)",
          "school_name": "서울대학교",
          "education_status": "졸업",
          "start_date": "2013-03-01T00:00:00",
          "end_date": "2017-02-28T00:00:00"
        }
      ],
      "experiences": [
        {
          "company_name": "넥스트러너스",
          "position": "Backend Developer",
          "start_date": "2020-03-01",
          "end_date": "2023-01-01",
          "description": "백엔드 개발자"
        },
        {
          "company_name": "오즈코딩스쿨",
          "position": "Backend Developer",
          "start_date": "2020-03-01",
          "end_date": "2023-01-01",
          "description": "백엔드 개발자"
        }
      ]
    }
    '''
                                ), # 요청 바디에서 수정할 데이터 수신 (JSON 문자열)
    file: UploadFile = File(None),  # 이미지 파일 업로드
    Authorization: str = Header(...),  # Authorization 헤더에서 토큰 수신
    db: AsyncSession = Depends(get_db_session)  # DB 세션 의존성 주입
):
    """
    url에 지정된 이력서 id에 해당하는 이력서를 수정할수 있다.
    jwt로 사용자를 확인하고 해당 사용자만 이력서를 수정 할 수 있다.
    수정 후 최신 이력서와 학력사항을 반환한다.
    """
    # 현재 인증된 사용자 정보를 가져옴
    user = await read_current_user(Authorization=Authorization, db=db)
    parsed_data = ResumeUpdate.model_validate_json(resume_data)
    if file and file.filename:
        try:
            image_url = await upload_image_to_ncp(file, folder="resumes")
            parsed_data.resume_image = image_url
            logger.info(f"✅ 수정 - 이미지 업로드 성공: {image_url}")
        except Exception as e:
            logger.error(f"❌ 수정 - 이미지 업로드 실패: {str(e)}")
            raise HTTPException(status_code=400, detail=f"이미지 업로드 실패: {str(e)}")
    try:
        updated_resume = await update_existing_resume(resumes_id, user.id, parsed_data, db)
    except Exception:
        raise HTTPException(status_code=500, detail="이력서 수정 중 문제가 발생했습니다.")
    return {"status": "success", "data": serialize_resume(updated_resume)}

# 특정 이력서를 삭제함
@router.delete("/resumes/{resumes_id}", tags=["이력서"])  # HTTP DELETE 메서드와 경로 파라미터, 태그 지정
async def delete_resume(
    resumes_id: int,  # URL 경로에서 삭제할 이력서 ID 수신
    Authorization: str = Header(...),  # Authorization 헤더에서 토큰 수신
    db: AsyncSession = Depends(get_db_session)  # DB 세션 의존성 주입
):
    """
    url에 지정된 이력서 id에 해당하는 이력서를 삭제한다.
    jwt로 사용자를 확인하고 해당 사용자만 이력서를 삭제 할 수 있다.
    """
    # 현재 인증된 사용자 정보를 가져옴
    user = await read_current_user(Authorization=Authorization, db=db)
    try:
        await delete_resume_by_id(resumes_id, user.id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success", "message": "이력서가 삭제되었습니다."}