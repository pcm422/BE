from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.models import JobApplication, Resume, JobPosting, CompanyUser, User
from app.domains.job_applications.schemas import ApplicationStatusEnum
from app.domains.job_applications.utils import build_resume_snapshot, send_resume_email
from app.core.logger import logger


# 사용자가 채용공고에 대해 본인의 이력서로 지원
async def create_application(
    user_id: int,  # 사용자 ID
    job_posting_id: int,  # 채용공고 ID
    session: AsyncSession,  # DB 세션
) -> JobApplication:
    """사용자의 이력서를 채용공고에 지원"""
    try:
        logger.info("이력서 조회 시작")  # 이력서 조회 로그 출력
        resume = await session.execute(
            select(Resume)
            .filter(Resume.user_id == user_id)  # 해당 사용자의 이력서 중
            .order_by(Resume.created_at.desc())  # 가장 최근에 생성된 것
            .limit(1)
        )
        resume = resume.scalar_one_or_none()  # 단일 객체 반환
        if not resume:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "지원할 이력서가 없습니다.")  # 없으면 404 반환

        logger.info("채용공고 검증 시작")  # 채용공고 조회 로그 출력
        job = await session.get(JobPosting, job_posting_id)  # 채용공고 조회
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "채용공고가 존재하지 않습니다.")

        logger.info("중복 지원 검증 시작")  # 기존 지원 여부 체크
        existing_app = await session.execute(
            select(JobApplication).filter(
                JobApplication.user_id == user_id,
                JobApplication.job_posting_id == job_posting_id,
            )
        )
        if existing_app.scalar_one_or_none():  # 이미 지원한 경우
            raise HTTPException(status.HTTP_409_CONFLICT, "이미 지원한 공고입니다.")

        snapshot = build_resume_snapshot(resume)  # 이력서 스냅샷 생성

        new_app = JobApplication(
            user_id=user_id,  # 사용자 ID
            resume_id=resume.id,  # 이력서 ID
            job_posting_id=job_posting_id,  # 채용공고 ID
            resumes_data=snapshot,  # 스냅샷 데이터
            status=ApplicationStatusEnum.applied,  # 초기 상태
        )

        try:
            logger.info("신규 지원 레코드 추가 시작")  # DB 삽입 시작 로그
            session.add(new_app)  # 새 지원 추가
            await session.commit()  # 커밋
            await session.refresh(new_app)  # 최신 상태 반영
        except Exception as e:
            await session.rollback()  # 에러 발생 시 롤백
            logger.warning(f"DB 커밋 중 오류: {e}")  # 경고 로그 출력
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 생성 중 오류: {str(e)}")

        logger.info("이메일 발송 시작")  # 이메일 전송 로그
        author = await session.get(CompanyUser, job.author_id)  # 기업 사용자 정보 조회
        applicant = await session.get(User, user_id)  # 지원자 정보 조회

        if author and author.company:  # 회사 정보가 있으면
            email = author.company.manager_email  # 담당자 이메일 가져오기
            if not email:
                logger.warning(f"이메일 주소가 존재하지 않아 전송이 중단되었습니다. company_id={author.company.id}")
            else:
                logger.info(f"이메일 전송 시도: {email}")
                await send_resume_email(  # 이메일 전송 함수 호출
                    job_title=job.title,
                    applicant=applicant,
                    resume=snapshot,
                    to_email=email
                )
        res = await session.execute(
            select(JobApplication)
            .options(selectinload(JobApplication.job_posting))
            .where(JobApplication.id == new_app.id)
        )
        new_app = res.scalar_one()  # 관계 필드 포함된 완전한 객체로 다시 불러오기
        return new_app  # 최종 결과 반환
    except HTTPException:
        raise  # HTTP 예외는 그대로 다시 발생
    except SQLAlchemyError as e:
        await session.rollback()  # DB 예외 발생 시 롤백
        logger.warning(f"SQLAlchemy 에러: {e}")  # 경고 로그 출력
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 생성 중 오류: {str(e)}")
    except Exception as e:
        logger.warning(f"예상치 못한 오류 발생: {e}")  # 예외 로그 출력
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "예상치 못한 오류 발생")


async def get_user_applications(
    user_id: int, session: AsyncSession
) -> List[dict]:
    """사용자가 지원한 모든 공고 내역 조회 (공고 정보 포함)"""
    try:
        res = await session.execute(
            select(JobApplication, JobPosting)
            .join(JobPosting, JobApplication.job_posting_id == JobPosting.id)
            .filter(JobApplication.user_id == user_id)
            .order_by(JobApplication.created_at.desc())
        )
        results = res.all()  # (지원, 채용공고) 튜플 목록

        applications = []
        for application, posting in results:
            applications.append({  # 필요한 정보만 dict로 정리
                "id": application.id,
                "user_id": application.user_id,
                "job_posting_id": application.job_posting_id,
                "job_posting": {
                    "id": posting.id,
                    "title": posting.title,
                    "company_id": posting.company_id,
                    "recruit_period_start": posting.recruit_period_start,
                    "recruit_period_end": posting.recruit_period_end,
                    "work_address": posting.work_address,
                    "work_place_name": posting.work_place_name,
                },
                "resumes_data": application.resumes_data,
                "status": application.status.value,
                "created_at": application.created_at,
                "updated_at": application.updated_at,
            })

        return applications  # 리스트 반환
    except SQLAlchemyError as e:
        await session.rollback()
        logger.warning(f"지원 내역 조회 중 SQLAlchemy 에러: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 내역 조회 중 오류: {str(e)}")


async def get_user_application_detail(
    user_id: int, job_posting_id: int, session: AsyncSession
) -> Optional[JobApplication]:
    """사용자가 특정 공고에 지원한 내역 단건 조회"""
    try:
        res = await session.execute(
            select(JobApplication)
            .options(selectinload(JobApplication.job_posting))  # 관계 미리 로딩
            .filter(
                JobApplication.user_id == user_id,
                JobApplication.job_posting_id == job_posting_id,
            )
        )
        return res.scalar_one_or_none()  # 단건 반환
    except SQLAlchemyError as e:
        await session.rollback()
        logger.warning(f"지원 상세 조회 중 SQLAlchemy 에러: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 내역 조회 중 오류: {str(e)}")


async def delete_application(
    application_id: int, user_id: int, session: AsyncSession
) -> None:
    """사용자가 자신의 지원을 취소(삭제)"""
    try:
        res = await session.execute(
            select(JobApplication).filter(
                JobApplication.id == application_id,
                JobApplication.user_id == user_id,
            )
        )
        app = res.scalar_one_or_none()
        if app is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "지원 내역이 없습니다.")
        await session.delete(app)
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.warning(f"지원 삭제 중 SQLAlchemy 에러: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 취소 중 오류: {str(e)}")


async def get_company_applications(
    company_user: CompanyUser, session: AsyncSession
) -> List[JobApplication]:
    """기업유저가 자사 공고에 받은 모든 지원 리스트 조회"""
    try:
        res = await session.execute(
            select(JobApplication)
            .join(JobPosting)
            .filter(JobPosting.company_id == company_user.company_id)
            .order_by(JobApplication.created_at.desc())
        )
        return res.scalars().all()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.warning(f"회사 지원 내역 조회 중 SQLAlchemy 에러: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"회사 지원 내역 조회 중 오류: {str(e)}")


async def get_company_application_detail(
    company_user: CompanyUser, application_id: int, session: AsyncSession
) -> JobApplication:
    """기업유저가 특정 지원 상세 조회"""
    try:
        res = await session.execute(
            select(JobApplication)
            .join(JobPosting)
            .filter(
                JobApplication.id == application_id,
                JobPosting.company_id == company_user.company_id,
            )
        )
        app = res.scalar_one_or_none()
        if app is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "해당 지원을 찾을 수 없습니다.")
        return app
    except SQLAlchemyError as e:
        await session.rollback()
        logger.warning(f"지원 상세 조회 중 SQLAlchemy 에러: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 상세 조회 중 오류: {str(e)}")


async def update_application_status(
    company_user: CompanyUser,
    application_id: int,
    status_val: ApplicationStatusEnum,
    session: AsyncSession,
) -> JobApplication:
    """기업유저가 지원 상태를 변경"""
    try:
        app = await get_company_application_detail(company_user, application_id, session)  # 지원 내역 가져오기
        app.status = status_val  # 상태 값 변경
        await session.commit()  # DB 커밋
        await session.refresh(app)  # 상태 반영
        return app  # 결과 반환
    except SQLAlchemyError as e:
        await session.rollback()
        logger.warning(f"지원 상태 변경 중 SQLAlchemy 에러: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 상태 변경 중 오류: {str(e)}")
    except Exception as e:
        logger.warning(f"예상치 못한 오류 발생: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "예상치 못한 오류 발생")
