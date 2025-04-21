from app.models import Resume, ResumeEducation
from app.models.job_experience import ResumeExperience


# 이력서 객체를 직렬화하여 JSON 응답용 딕셔너리로 변환하는 함수
def serialize_resume(resume: Resume) -> dict:
    return {
        "id": resume.id,  # 이력서 고유 ID
        "user_id": resume.user_id,  # 이력서 작성자 사용자 ID
        "resume_image": resume.resume_image,  # 이력서 이미지 URL
        "desired_area": resume.desired_area,  # 희망 근무 지역
        "introduction": resume.introduction,  # 자기소개 내용
        "created_at": resume.created_at.isoformat() if resume.created_at else None,  # 생성일
        "updated_at": resume.updated_at.isoformat() if resume.updated_at else None,  # 수정일
        "educations": [serialize_education(edu) for edu in resume.educations] if resume.educations else [],
        # 학력사항 리스트
        "experiences": [serialize_experience(exp) for exp in resume.experiences] if resume.experiences else []
        # 경력사항 리스트
    }

# 교육 이력 객체를 직렬화하여 JSON 응답용 딕셔너리로 변환하는 함수
def serialize_education(education: ResumeEducation) -> dict:
    return {
        "id": education.id,  # 학력사항 고유 ID
        "education_type": education.education_type,  # 교육 유형 (예: 대졸, 대학원 등)
        "school_name": education.school_name,  # 학교명
        "education_status": education.education_status,  # 재학 중/졸업/휴학 등 상태
        "start_date": education.start_date.isoformat() if education.start_date else None,  # 입학일
        "end_date": education.end_date.isoformat() if education.end_date else None,  # 졸업(예정)일
        "created_at": education.created_at.isoformat() if education.created_at else None,  # 생성일
        "updated_at": education.updated_at.isoformat() if education.updated_at else None,  # 수정일
        "resumes_id": education.resumes_id  # 연결된 이력서 ID
    }


# 경력 이력 객체를 직렬화하여 JSON 응답용 딕셔너리로 변환하는 함수
def serialize_experience(exp: ResumeExperience) -> dict:
    return {
        "id": exp.id,  # 경력사항 고유 ID
        "company_name": exp.company_name,  # 경력사항의 회사명
        "position": exp.position,  # 경력사항의 직무/직급
        "start_date": exp.start_date.isoformat() if exp.start_date else None,  # 근무 시작일
        "end_date": exp.end_date.isoformat() if exp.end_date else None,  # 근무 종료일
        "description": exp.description,  # 업무 내용 등의 상세 설명
        "created_at": exp.created_at.isoformat() if exp.created_at else None,  # 생성일
        "updated_at": exp.updated_at.isoformat() if exp.updated_at else None,  # 수정일
        "resumes_id": exp.resume_id  # 연결된 이력서 ID
    }