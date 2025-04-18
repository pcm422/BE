from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from app.models import JobApplication, Resume, JobPosting, CompanyUser, User
from .schemas import ApplicationStatusEnum
from .utils import send_email, jinja_env


# 사용자가 채용공고에 대해 본인의 이력서로 지원
async def create_application(
    user_id: int,
    job_posting_id: int,
    session: AsyncSession,
) -> JobApplication:
    """사용자의 이력서를 채용공고에 지원"""
    try:
        result = await session.execute(
            select(Resume)
            .filter(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
        resume = result.scalar_one_or_none()
        if not resume:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "지원할 이력서가 없습니다.")

        res = await session.execute(
            select(JobPosting).filter(JobPosting.id == job_posting_id)  # 채용공고 검증
        )
        if res.scalar_one_or_none() is None:   # 없으면 예외
            raise HTTPException(status.HTTP_404_NOT_FOUND, "채용공고가 존재하지 않습니다.")

        res = await session.execute(
            select(JobApplication).filter(
                JobApplication.user_id == user_id,
                JobApplication.job_posting_id == job_posting_id,
            )  # 중복 지원 검증
        )
        if res.scalar_one_or_none():  # 있으면 예외
            raise HTTPException(status.HTTP_409_CONFLICT, "이미 지원한 공고입니다.")

        snapshot = {
            "resume_image": resume.resume_image,
            "desired_area": resume.desired_area,
            "introduction": resume.introduction,
            # 학력
            "educations": [
                {
                    "education_type": edu.education_type,
                    "school_name": edu.school_name,
                    "education_status": edu.education_status,
                    "start_date": edu.start_date.isoformat() if edu.start_date else None,
                    "end_date": edu.end_date.isoformat() if edu.end_date else None,
                }
                for edu in resume.educations
            ],
            # 경력
            "experiences": [
                {
                    "company_name": exp.company_name,
                    "position": exp.position,
                    "start_date": exp.start_date.isoformat() if exp.start_date else None,
                    "end_date": exp.end_date.isoformat() if exp.end_date else None,
                    "description": exp.description,
                }
                for exp in resume.experiences
            ],
        }

        new_app = JobApplication(   # 지원내역 생성
            user_id=user_id,
            resume_id=resume.id,
            job_posting_id=job_posting_id,
            resumes_data=snapshot,
            status=ApplicationStatusEnum.applied,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add(new_app)  # 신규 지원 레코드 추가
        await session.commit()  # 세션 커밋
        await session.refresh(new_app)  # 새로 추가된 레코드 새로 고침
        # 이메일 발송
        job = await session.get(JobPosting, job_posting_id)
        author = await session.get(CompanyUser, job.author_id)
        applicant = await session.get(User, user_id)

        if author and author.manager_email:
            template = jinja_env.get_template("resume_email.html")
            html = template.render(
                job_title=job.title,
                applicant=applicant,
                resume=snapshot  # snapshot 대신 resume 모델 직접 넘겨도 OK
            )
            await send_email(
                to_email=author.manager_email,
                subject=f"[{job.title}] 지원자 이력서",
                html_content=html,
                text_content="지원자 이력서를 확인해주세요."
            )

        return new_app  # 생성된 지원 반환
    except HTTPException:  # HTTP 예외 발생 시
        raise  # 예외 반환
    except SQLAlchemyError as e:  # SQLAlchemy 에러 발생 시
        await session.rollback()  # 세션 롤백
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 생성 중 오류: {str(e)}")  # 500 에러 발생

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
        app.updated_at = datetime.now()  # 업데이트 날짜 설정
        await session.commit()  # 세션 커밋
        await session.refresh(app)  # 새로 고침
        return app  # 결과 반환
    except SQLAlchemyError as e:  # SQLAlchemy 에러 발생 시
        await session.rollback()  # 세션 롤백
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"지원 상태 변경 중 오류: {str(e)}")  # 500 에러 발생