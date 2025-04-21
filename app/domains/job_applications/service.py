from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from app.models import JobApplication, Resume, JobPosting, CompanyUser, User
from .schemas import ApplicationStatusEnum
from .utils import build_resume_snapshot, send_resume_email
from ..resumes.router import logger


# 사용자가 채용공고에 대해 본인의 이력서로 지원
async def create_application(
    user_id: int,
    job_posting_id: int,
    session: AsyncSession,
) -> JobApplication:
    """사용자의 이력서를 채용공고에 지원"""
    try:
        logger.info("이력서 조회 시작")
        resume = await session.execute(
            select(Resume)
            .filter(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
        resume = resume.scalar_one_or_none()
        if not resume:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "지원할 이력서가 없습니다.")

        logger.info("채용공고 검증 시작")
        job = await session.get(JobPosting, job_posting_id)
        if job is None:   # 없으면 예외
            raise HTTPException(status.HTTP_404_NOT_FOUND, "채용공고가 존재하지 않습니다.")

        logger.info("중복 지원 검증 시작")
        existing_app = await session.execute(
            select(JobApplication).filter(
                JobApplication.user_id == user_id,
                JobApplication.job_posting_id == job_posting_id,
            )
        )
        if existing_app.scalar_one_or_none():  # 있으면 예외
            raise HTTPException(status.HTTP_409_CONFLICT, "이미 지원한 공고입니다.")

        snapshot = build_resume_snapshot(resume)

        new_app = JobApplication(   # 지원내역 생성
            user_id=user_id,
            resume_id=resume.id,
            job_posting_id=job_posting_id,
            resumes_data=snapshot,
            status=ApplicationStatusEnum.applied,
        )

        try:
            logger.info("신규 지원 레코드 추가 시작")
            session.add(new_app)  # 신규 지원 레코드 추가
            await session.commit()  # 세션 커밋
            await session.refresh(new_app)  # 새로 추가된 레코드 새로 고침
        except Exception as e:
            await session.rollback()  # 세션 롤백
            logger.warning(f"DB 커밋 중 오류: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 생성 중 오류: {str(e)}")  # 500 에러 발생

        logger.info("이메일 발송 시작")
        author = await session.get(CompanyUser, job.author_id)
        applicant = await session.get(User, user_id)

        if author and author.company:
            email = author.company.manager_email
            if not email:
                logger.warning(f"이메일 주소가 존재하지 않아 전송이 중단되었습니다. company_id={author.company.id}")
            else:
                logger.info(f"이메일 전송 시도: {email}")
                await send_resume_email(
                    job_title=job.title,
                    applicant=applicant,
                    resume=snapshot,
                    to_email=email
                )

        return new_app  # 생성된 지원 반환
    except HTTPException:  # HTTP 예외 발생 시
        raise  # 예외 반환
    except SQLAlchemyError as e:  # SQLAlchemy 에러 발생 시
        await session.rollback()  # 세션 롤백
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 생성 중 오류: {str(e)}")  # 500 에러 발생
    except Exception as e:  # 예상치 못한 에러 발생 시
        logger.warning(f"예상치 못한 오류 발생: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "예상치 못한 오류 발생")  # 500 에러 발생

# 사용자가 지원한 모든 공고 내역을 조회
async def get_user_applications(
    user_id: int, session: AsyncSession
) -> List[JobApplication]:
    """사용자가 지원한 모든 공고 내역 조회"""
    try:  # 예외 처리 시작
        res = await session.execute(
            select(JobApplication)
            .filter(JobApplication.user_id == user_id)
            .order_by(JobApplication.created_at.desc())  # 사용자 지원 내역 조회
        )
        return res.scalars().all()  # 결과 반환
    except SQLAlchemyError as e:  # SQLAlchemy 에러 발생 시
        await session.rollback()  # 세션 롤백
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 내역 조회 중 오류: {str(e)}")  # 500 에러 발생

async def get_user_application_detail(
    user_id: int, job_posting_id: int, session: AsyncSession
) -> Optional[JobApplication]:
    """사용자가 특정 공고에 지원한 내역 단건 조회"""
    try:  # 예외 처리 시작
        res = await session.execute(
            select(JobApplication).filter(
                JobApplication.user_id == user_id,
                JobApplication.job_posting_id == job_posting_id,  # 특정 지원 내역 조회
            )
        )
        return res.scalar_one_or_none()  # 결과 반환
    except SQLAlchemyError as e:  # SQLAlchemy 에러 발생 시
        await session.rollback()  # 세션 롤백
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 내역 조회 중 오류: {str(e)}")  # 500 에러 발생

# 사용자가 자신의 채용지원을 취소
async def delete_application(
    application_id: int, user_id: int, session: AsyncSession
) -> None:
    """사용자가 자신의 지원을 취소(삭제)"""
    try:  # 예외 처리 시작
        res = await session.execute(
            select(JobApplication).filter(
                JobApplication.id == application_id,
                JobApplication.user_id == user_id,  # 지원 내역 조회
            )
        )
        app = res.scalar_one_or_none()  # 지원 내역 가져오기
        if app is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "지원 내역이 없습니다.")
        await session.delete(app)  # 지원 내역 삭제
        await session.commit()  # 세션 커밋
    except SQLAlchemyError as e:  # SQLAlchemy 에러 발생 시
        await session.rollback()  # 세션 롤백
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 취소 중 오류: {str(e)}")  # 500 에러 발생

# 기업 유저가 자사 공고의 모든 지원내역 조회
async def get_company_applications(
    company_user: CompanyUser, session: AsyncSession
) -> List[JobApplication]:
    """기업유저가 자사 공고에 받은 모든 지원 리스트 조회"""
    try:  # 예외 처리 시작
        res = await session.execute(
            select(JobApplication)
            .join(JobPosting)
            .filter(JobPosting.company_id == company_user.company_id)
            .order_by(JobApplication.created_at.desc())  # 회사 지원 내역 조회
        )
        return res.scalars().all()  # 결과 반환
    except SQLAlchemyError as e:  # SQLAlchemy 에러 발생 시
        await session.rollback()  # 세션 롤백
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"회사 지원 내역 조회 중 오류: {str(e)}")  # 500 에러 발생

async def get_company_application_detail(
    company_user: CompanyUser, application_id: int, session: AsyncSession
) -> JobApplication:
    """기업유저가 특정 지원 상세 조회"""
    try:  # 예외 처리 시작
        res = await session.execute(
            select(JobApplication)
            .join(JobPosting)
            .filter(
                JobApplication.id == application_id,
                JobPosting.company_id == company_user.company_id,  # 특정 지원 내역 조회
            )
        )
        app = res.scalar_one_or_none()  # 지원 내역 가져오기
        if app is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "해당 지원을 찾을 수 없습니다.")
        return app  # 결과 반환
    except SQLAlchemyError as e:  # SQLAlchemy 에러 발생 시
        await session.rollback()  # 세션 롤백
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 상세 조회 중 오류: {str(e)}")  # 500 에러 발생

# 기업유저가 채용이력의 대한 지원상태 변경
async def update_application_status(
    company_user: CompanyUser,
    application_id: int,
    status_val: ApplicationStatusEnum,
    session: AsyncSession,
) -> JobApplication:
    """기업유저가 지원 상태를 변경"""
    try:  # 예외 처리 시작
        app = await get_company_application_detail(company_user, application_id, session)  # 지원 내역 가져오기
        app.status = status_val  # 상태 변경
        await session.commit()  # 세션 커밋
        await session.refresh(app)  # 새로 고침
        return app  # 결과 반환
    except SQLAlchemyError as e:  # SQLAlchemy 에러 발생 시
        await session.rollback()  # 세션 롤백
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 상태 변경 중 오류: {str(e)}")  # 500 에러 발생
    except Exception as e:  # 예상치 못한 에러 발생 시
        logger.warning(f"예상치 못한 오류 발생: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "예상치 못한 오류 발생")  # 500 에러 발생