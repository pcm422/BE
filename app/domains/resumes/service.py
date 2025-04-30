from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import delete
from typing import Optional

from app.models import Resume, ResumeEducation
from app.domains.resumes.schemas import ResumeCreate, ResumeUpdate
from app.models.job_experience import ResumeExperience

# 현재 사용자의 최신 이력서를 조회하는 함수
async def get_resume_for_user(user_id: int, db: AsyncSession) -> Optional[Resume]:
    result = await db.execute(
        select(Resume)
        .options(selectinload(Resume.educations), selectinload(Resume.experiences))  # 학력, 경력 관계를 미리 로드
        .filter(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())  # 생성일 기준 내림차순 정렬
        .limit(1)  # 가장 마지막에 생성된 이력서 하나만 조회
    )
    return result.scalar_one_or_none()  # 조회 결과가 있으면 반환


# 새 이력서를 생성하는 함수
async def create_new_resume(resume_data: ResumeCreate, db: AsyncSession) -> Resume:
    # 새 이력서(Resume) 객체 생성
    new_resume = Resume(
        user_id=resume_data.user_id,               # 사용자 ID
        resume_image=resume_data.resume_image,      # 이력서 이미지
        desired_area=resume_data.desired_area,      # 희망 지역
        introduction=resume_data.introduction,      # 자기소개
    )

    # 만약 educations 필드가 있다면 반복을 통해 학력 추가
    if resume_data.educations:
        for edu_data in resume_data.educations:
            new_education = ResumeEducation(
                resumes_id=resume_data.user_id,              # 이력서 아이디 자동 연결
                education_type=edu_data.education_type,      # 학력 유형
                school_name=edu_data.school_name,            # 학교명
                education_status=edu_data.education_status,  # 학력 상태
                start_date=edu_data.start_date,              # 입학일
                end_date=edu_data.end_date,                  # 졸업(예정)일
            )
            new_resume.educations.append(new_education)  # 학력사항 리스트에 추가

    # 만약 experiences 필드가 있다면 반복하여 경력사항을 추가
    if resume_data.experiences:
        for exp_data in resume_data.experiences:
            new_experience = ResumeExperience(
                resume=new_resume,                           # Resume 관계하여 외래키가 자동 할당되게
                company_name=exp_data.company_name,          # 경력 회사명
                position=exp_data.position,                  # 직무/직급
                start_date=exp_data.start_date,              # 근무 시작일
                end_date=exp_data.end_date,                  # 근무 종료일
                description=exp_data.description,            # 업무 내용 등 상세 정보
            )
            new_resume.experiences.append(new_experience)  # 경력사항 리스트에 추가

    db.add(new_resume)  # 새 이력서 객체를 DB 세션에 추가

    try:
        await db.commit()  # 커밋
        await db.refresh(new_resume)  # 반영(리프레쉬)

        # educations와 experiences 관계를 미리 로드하기 위해 다시 조회
        result = await db.execute(
            select(Resume)
            .options(selectinload(Resume.educations), selectinload(Resume.experiences))
            .filter(Resume.id == new_resume.id)
        )
        new_resume = result.scalar_one_or_none()

    except Exception as e:
        # 예외 발생 시 롤백
        await db.rollback()
        raise HTTPException(status_code=500, detail="이력서 및 관련 정보 생성 중 문제가 발생했습니다: " + str(e))

    # 생성된 Resume 객체를 반환
    return new_resume

# 특정 이력서를 수정하는 함수
async def update_existing_resume(resumes_id: int, user_id: int, resume_data: ResumeUpdate, db: AsyncSession) -> Resume:
    # DB에서 수정할 이력서가 현재 사용자의 소유인지 확인하며 조회
    result = await db.execute(
        select(Resume).filter(Resume.id == resumes_id, Resume.user_id == user_id)
    )
    resume = result.scalar_one_or_none()  # 조회 결과에서 단일 이력서 객체를 추출
    if resume is None:   # 없으면 예외처리
        raise HTTPException(status_code=404, detail="이력서를 찾을 수 없습니다.")

    # 요청 데이터에 포함된 각 필드가 None이 아닐 경우 해당 필드를 수정
    if resume_data.resume_image is not None:
        resume.resume_image = resume_data.resume_image  # 이력서 이미지 URL 수정
    if resume_data.desired_area is not None:
        resume.desired_area = resume_data.desired_area  # 희망 지역 수정
    if resume_data.introduction is not None:
        resume.introduction = resume_data.introduction  # 자기소개 내용 수정
    ### 학력사항과 경력사항은 있으면 삭제 후 생성 없으면 그대로 진행
    # 학력사항 업데이트
    if resume_data.educations is not None:
        # 기존 학력사항을 bulk delete로 제거
        await db.execute(
            delete(ResumeEducation).where(ResumeEducation.resumes_id == resume.id)
        )
        await db.flush()  # 삭제 즉시 반영

        resume.educations = [
            ResumeEducation(
                education_type=edu_data.education_type,
                school_name=edu_data.school_name,
                education_status=edu_data.education_status,
                start_date=edu_data.start_date,
                end_date=edu_data.end_date,
            )
            for edu_data in resume_data.educations
        ]

    # 경력사항 업데이트
    if resume_data.experiences is not None:
        # 기존 경력사항을 bulk delete로 제거
        await db.execute(
            delete(ResumeExperience).where(ResumeExperience.resume_id == resume.id)
        )
        await db.flush()  # 삭제 즉시 반영

        resume.experiences = [
            ResumeExperience(
                company_name=exp_data.company_name,
                position=exp_data.position,
                start_date=exp_data.start_date,
                end_date=exp_data.end_date,
                description=exp_data.description,
            )
            for exp_data in resume_data.experiences
        ]

    try:
        # DB에 변경 사항을 커밋함 (수정 저장)
        await db.commit()
        # 수정 후, educations 및 experiences 관계를 미리 로드하여 다시 조회
        result = await db.execute(
            select(Resume)
            .options(selectinload(Resume.educations), selectinload(Resume.experiences))
            .filter(Resume.id == resumes_id)
        )
        resume = result.scalar_one_or_none()

    except Exception as e:
        # 예외 발생 시 롤백 후 500 에러 응답
        await db.rollback()
        raise HTTPException(status_code=500, detail="이력서 업데이트 중 오류 발생: " + str(e))

    # 수정된 Resume 객체를 반환
    return resume


# 특정 이력서를 삭제하는 함수
async def delete_resume_by_id(resumes_id: int, user_id: int, db: AsyncSession) -> None:
    # DB에서 삭제할 이력서가 사용자의 소유인지 확인하며 조회
    result = await db.execute(
        select(Resume).filter(Resume.id == resumes_id, Resume.user_id == user_id)
    )
    resume = result.scalar_one_or_none()  # 조회 결과에서 단일 이력서 객체를 추출
    if resume is None:
        raise HTTPException(status_code=404, detail="이력서를 찾을 수 없습니다.")

    await db.delete(resume)  # 이력서 객체 삭제 요청
    try:
        # 삭제 후 변경 사항을 DB에 커밋
        await db.commit()
    except Exception as e:
        # 예외 발생 시 롤백 후 오류 발생
        await db.rollback()
        raise HTTPException(status_code=500, detail="이력서 삭제 중 오류 발생: " + str(e))