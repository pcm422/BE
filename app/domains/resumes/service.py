from app.models import Resume, ResumeEducation
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.domains.resumes.schemas import ResumeCreate, ResumeUpdate

# 이력서 객체를 직렬화하여 JSON 응답용 딕셔너리로 변환하는 함수
def serialize_resume(resume: Resume) -> dict:
    return {  # 이력서 필드들을 딕셔너리 형태로 매핑
        "id": resume.id,  # 이력서 고유 ID
        "user_id": resume.user_id,  # 사용자 ID
        "resume_image": resume.resume_image,  # 이력서 이미지 URL
        "company_name": resume.company_name,  # 회사명
        "position": resume.position,  # 직무 또는 직급
        "work_period_start": resume.work_period_start.isoformat() if resume.work_period_start else None,  # 근무 시작일 (ISO 포맷)
        "work_period_end": resume.work_period_end.isoformat() if resume.work_period_end else None,  # 근무 종료일 (ISO 포맷)
        "desired_area": resume.desired_area,  # 희망 지역
        "introduction": resume.introduction,  # 자기소개 내용
        "created_at": resume.created_at.isoformat() if resume.created_at else None,  # 생성일 (ISO 포맷)
        "updated_at": resume.updated_at.isoformat() if resume.updated_at else None,  # 수정일 (ISO 포맷)
        "educations": [serialize_education(edu) for edu in resume.educations] if resume.educations else []  # 관련 교육 이력 리스트
    }

# 교육 이력 객체를 직렬화하여 JSON 응답용 딕셔너리로 변환하는 함수
def serialize_education(education: ResumeEducation) -> dict:
    return {
        "id": education.id,
        "education_type": education.education_type,  # .value 제거
        "school_name": education.school_name,
        "education_status": education.education_status,  # .value 제거
        "start_date": education.start_date.isoformat() if education.start_date else None,
        "end_date": education.end_date.isoformat() if education.end_date else None,
        "created_at": education.created_at.isoformat() if education.created_at else None,
        "updated_at": education.updated_at.isoformat() if education.updated_at else None,
        "resumes_id": education.resumes_id
    }

# 현재 사용자의 최신 이력서를 조회하는 함수
async def get_resume_for_user(user_id: int, db: AsyncSession) -> Resume | None:
    result = await db.execute(
        select(Resume)
        .options(selectinload(Resume.educations))  # educations 관계 미리 로드 설정
        .filter(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())  # 생성일 기준 내림차순 정렬
        .limit(1)  # 가장 마지막에 생성된 이력서 하나만 조회
    )
    return result.scalar_one_or_none()  #반환

# 새 이력서를 생성하는 함수
async def create_new_resume(resume_data: ResumeCreate, db: AsyncSession) -> Resume:
    # 새 이력서(Resume) 객체 생성
    new_resume = Resume(
        user_id=resume_data.user_id,               # 사용자 ID
        resume_image=resume_data.resume_image,      # 이력서 이미지
        company_name=resume_data.company_name,      # 회사명
        position=resume_data.position,              # 직급/직무
        work_period_start=resume_data.work_period_start,  # 근무 시작일
        work_period_end=resume_data.work_period_end,      # 근무 종료일
        desired_area=resume_data.desired_area,      # 희망 지역
        introduction=resume_data.introduction,      # 자기소개
        created_at=datetime.now(),                  # 생성일
        updated_at=datetime.now()                   # 수정일
    )

    # 만약 educations 필드가 있다면 반복을 통해 학력 추가
    if resume_data.educations:
        # 각 EducationCreate 아이템에 대해 ResumeEducation 객체를 생성하고,
        # new_resume.educations 리스트에 추가
        for edu_data in resume_data.educations:
            new_education = ResumeEducation(
                resumes_id=resume_data.user_id,           # 관계 설정: 나중에 overwrite할 것
                education_type=edu_data.education_type,    # 교육 유형
                school_name=edu_data.school_name,          # 학교명
                education_status=edu_data.education_status,# 학력 상태
                start_date=edu_data.start_date,            # 입학일
                end_date=edu_data.end_date,                # 졸업(예정)일
                created_at=datetime.now(),                 # 생성일
                updated_at=datetime.now(),                 # 수정일
            )
            new_resume.educations.append(new_education)

    db.add(new_resume)

    try:
        await db.commit()  # 커밋
        await db.refresh(new_resume)  # 반영(리프레쉬)

        # educations 관계를 미리 로드
        result = await db.execute(
            select(Resume)
            .options(selectinload(Resume.educations))
            .filter(Resume.id == new_resume.id)
        )
        new_resume = result.scalar_one_or_none()

    except Exception as e:
        # 예외 발생 시 롤백
        await db.rollback()
        raise Exception("이력서 및 학력사항 생성 중 문제가 발생했습니다.")

    # 생성된 Resume 객체를 반환
    return new_resume

# 특정 이력서를 수정하는 함수
async def update_existing_resume(resumes_id: int, user_id: int, resume_data: ResumeUpdate, db: AsyncSession) -> Resume:
    # DB에서 수정할 이력서가 현재 사용자의 소유인지 확인하며 조회
    result = await db.execute(select(Resume).filter(Resume.id == resumes_id, Resume.user_id == user_id))
    resume = result.scalar_one_or_none()  # 조회 결과에서 단일 이력서 객체 추출
    if resume is None:
        raise Exception("이력서를 찾을 수 없습니다.")
    # 요청 데이터에 포함된 각 필드가 None이 아닐 경우 해당 필드를 수정
    if resume_data.resume_image is not None:
        resume.resume_image = resume_data.resume_image  # 이력서 이미지 URL 수정
    if resume_data.company_name is not None:
        resume.company_name = resume_data.company_name  # 회사명 수정
    if resume_data.position is not None:
        resume.position = resume_data.position  # 직무/직급 수정
    if resume_data.work_period_start is not None:
        resume.work_period_start = resume_data.work_period_start  # 근무 시작일 수정
    if resume_data.work_period_end is not None:
        resume.work_period_end = resume_data.work_period_end  # 근무 종료일 수정
    if resume_data.desired_area is not None:
        resume.desired_area = resume_data.desired_area  # 희망 지역 수정
    if resume_data.introduction is not None:
        resume.introduction = resume_data.introduction  # 자기소개 내용 수정
    # 수정일을 현재 시간으로 갱신
    resume.updated_at = datetime.now()

    if resume_data.educations is not None:
        # 기존 학력사항을 모두 삭제
        await db.execute(
            select(ResumeEducation)
            .filter(ResumeEducation.resumes_id == resume.id)
        )
        result = await db.execute(
            select(ResumeEducation).filter(ResumeEducation.resumes_id == resume.id)
        )
        existing_educations = result.scalars().all()
        for edu in existing_educations:
            await db.delete(edu)

        # 새 학력사항을 추가
        for edu_data in resume_data.educations:
            new_education = ResumeEducation(
                resumes_id=resume.id,
                education_type=edu_data.education_type,
                school_name=edu_data.school_name,
                education_status=edu_data.education_status,
                start_date=edu_data.start_date,
                end_date=edu_data.end_date,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(new_education)

    try:
        # DB에 변경 사항을 커밋함 (수정 저장)
        await db.commit()
        result = await db.execute(
            select(Resume)
            .options(selectinload(Resume.educations))
            .filter(Resume.id == resumes_id)
        )
        resume = result.scalar_one_or_none()

    except Exception as e:
        # 예외 발생 시 롤백 후 500 에러 응답
        await db.rollback()
        raise Exception("이력서 업데이트 중 오류 발생: " + str(e))
    # 수정된 Resume 객체를 반환
    return resume

# 특정 이력서를 삭제하는 함수
async def delete_resume_by_id(resumes_id: int, user_id: int, db: AsyncSession) -> None:
    # DB에서 삭제할 이력서가 사용자의 소유인지 확인하며 조회
    result = await db.execute(select(Resume).filter(Resume.id == resumes_id, Resume.user_id == user_id))
    resume = result.scalar_one_or_none()  # 조회 결과에서 단일 이력서 객체 추출
    if resume is None:
        raise Exception("이력서를 찾을 수 없습니다.")
    # 관련 학력사항을 먼저 삭제
    for edu in resume.educations:
        await db.delete(edu)
    # DB 세션에서 해당 이력서 객체를 삭제 요청
    await db.delete(resume)
    try:
        # 삭제 후 변경 사항을 DB에 커밋
        await db.commit()
    except Exception as e:
        # 예외 발생 시 롤백 후 오류 발생
        await db.rollback()
        raise Exception("이력서 삭제 중 오류 발생: " + str(e))