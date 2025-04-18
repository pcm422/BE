from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.domains.users.router import read_current_user
from app.core.utils import get_current_company_user

from .schemas import (
    ResumeApplyCreate, JobApplicationRead, JobApplicationStatusUpdate
)
from .service import (
    create_application, get_user_applications, get_user_application_detail,
    delete_application, get_company_applications,
    get_company_application_detail, update_application_status
)

router = APIRouter(prefix="/applications", tags=["지원내역"])  # API 라우터 생성, 경로 접두사와 태그 설정

# 사용자: 이력서로 지원
@router.post(
    "",
    response_model=JobApplicationRead,
    status_code=status.HTTP_201_CREATED,
    summary="이력서 자동 선택 지원 (JWT 인증)",
    description="JWT 토큰으로 인증된 사용자(user_id)의 최신 이력서로 채용공고에 지원합니다."
)
async def apply_with_resume(
    payload: ResumeApplyCreate,                    # 요청 본문: job_posting_id
    db: AsyncSession = Depends(get_db_session),    # DB 세션 주입
    user = Depends(read_current_user),             # JWT -> User 모델 주입
):
    """
    jwt토큰을 통해 user_id를 얻고 최신 이력서를 찾아 채용공고에 지원하는 api
    """
    # 서비스 호출: JWT로부터 받은 user.id와 payload.job_posting_id 사용
    application = await create_application(
        user_id=user.id,                           # 인증된 사용자 ID
        job_posting_id=payload.job_posting_id,     # 요청된 공고 ID
        session=db                                # DB 세션
    )
    return application  # 생성된 지원 내역 반환

# 사용자: 모든 지원 내역 조회
@router.get(
    "",
    response_model=list[JobApplicationRead],  # 응답 모델 설정
    summary="내 모든 지원 조회",  # 요약 설명
    description="로그인한 사용자가 지원한 전체 공고 내역을 반환합니다."  # 상세 설명
)
async def read_my_applications(  # 사용자의 모든 지원 내역을 조회하는 비동기 핸들러
    db: AsyncSession = Depends(get_db_session),  # 데이터베이스 세션 의존성 주입
    user = Depends(read_current_user)  # 현재 사용자 의존성 주입
):
    return await get_user_applications(user.id, db)  # 사용자 ID로 모든 지원 내역 조회

# 사용자: 특정 공고 지원 내역 조회
@router.get(
    "/posting/{job_posting_id}",
    response_model=JobApplicationRead,  # 응답 모델 설정
    summary="특정 공고 지원 조회",  # 요약 설명
    description="로그인한 사용자가 지정 공고에 지원한 내역 단건을 조회합니다."  # 상세 설명
)
async def read_my_application_detail(  # 특정 공고의 지원 내역을 조회하는 비동기 핸들러
    job_posting_id: int,  # 경로 매개변수로 받은 채용 공고 ID
    db: AsyncSession = Depends(get_db_session),  # 데이터베이스 세션 의존성 주입
    user = Depends(read_current_user)  # 현재 사용자 의존성 주입
):
    app = await get_user_application_detail(user.id, job_posting_id, db)  # 특정 공고에 대한 사용자 지원 내역 조회
    if app is None:  # 지원 내역이 없을 경우
        raise HTTPException(status.HTTP_404_NOT_FOUND, "지원 내역을 찾을 수 없습니다.")  # 404 예외 발생
    return app  # 지원 내역 반환

# 사용자: 지원 취소
@router.delete(
    "/{application_id}",
    status_code=status.HTTP_200_OK,  # 성공 시 204 상태 코드 반환
    summary="지원 취소",  # 요약 설명
    description="사용자가 본인의 지원을 취소(삭제)합니다."  # 상세 설명
)
async def cancel_my_application(  # 지원 취소를 처리하는 비동기 핸들러
    application_id: int,  # 경로 매개변수로 받은 지원 ID
    db: AsyncSession = Depends(get_db_session),  # 데이터베이스 세션 의존성 주입
    user = Depends(read_current_user)  # 현재 사용자 의존성 주입
):
    await delete_application(application_id, user.id, db)  # 지원 삭제 서비스 호출
    return {
        "status": "success",
        "message": "지원취소가 정상적으로 처리되었습니다.",
    }  # 결과 반환

# 기업: 자사 전체 지원 조회
@router.get(
    "/company",
    response_model=list[JobApplicationRead],  # 응답 모델 설정
    summary="기업 전체 지원 조회",  # 요약 설명
    description="기업유저가 본인의 기업 공고에 지원된 전체 이력서를 조회합니다."  # 상세 설명
)
async def company_list_applications(  # 기업의 전체 지원 내역을 조회하는 비동기 핸들러
    db: AsyncSession = Depends(get_db_session),  # 데이터베이스 세션 의존성 주입
    company_user = Depends(get_current_company_user)  # 현재 기업 사용자 의존성 주입
):
    return await get_company_applications(company_user, db)  # 기업 사용자의 지원 내역 조회

# 기업: 특정 지원 상세 조회
@router.get(
    "/company/{application_id}",
    response_model=JobApplicationRead,  # 응답 모델 설정
    summary="기업 지원 상세 조회",  # 요약 설명
    description="기업유저가 본인의 기업에 지원된 특정 이력서를 상세 조회합니다."  # 상세 설명
)
async def company_application_detail(  # 특정 지원 내역을 조회하는 비동기 핸들러
    application_id: int,  # 경로 매개변수로 받은 지원 ID
    db: AsyncSession = Depends(get_db_session),  # 데이터베이스 세션 의존성 주입
    company_user = Depends(get_current_company_user)  # 현재 기업 사용자 의존성 주입
):
    return await get_company_application_detail(company_user, application_id, db)  # 특정 지원 내역 조회

# 기업: 지원 상태 변경
@router.patch(
    "/company/{application_id}/status",
    response_model=JobApplicationRead,  # 응답 모델 설정
    summary="기업 지원 상태 변경",  # 요약 설명
    description="기업유저가 지원자의 상태(서류통과·합격 등)를 변경합니다."  # 상세 설명
)
async def company_change_status(  # 지원 상태를 변경하는 비동기 핸들러
    application_id: int,  # 경로 매개변수로 받은 지원 ID
    payload: JobApplicationStatusUpdate,  # 요청 본문으로 받은 지원 상태 업데이트 데이터
    db: AsyncSession = Depends(get_db_session),  # 데이터베이스 세션 의존성 주입
    company_user = Depends(get_current_company_user)  # 현재 기업 사용자 의존성 주입
):
    return await update_application_status(  # 지원 상태 업데이트 서비스 호출
        company_user=company_user,  # 기업 사용자
        application_id=application_id,  # 지원 ID
        status_val=payload.status,  # 업데이트할 상태 값
        session=db  # 데이터베이스 세션
    )  # 업데이트된 지원 내역 반환