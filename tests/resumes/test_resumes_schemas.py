import pytest
from app.domains.resumes.schemas import ResumeCreate, EducationCreate, ExperienceCreate

def test_resume_create_schema_validation():
    resume = ResumeCreate(
        user_id=1,
        resume_image="",
        desired_area="서울",
        introduction="테스트 이력서",
        educations=[
            EducationCreate(
                education_type="고등학교",
                school_name="서울고등학교",
                education_status="졸업"
            )
        ],
        experiences=[
            ExperienceCreate(
                company_name="회사",
                position="백엔드",
                description="설명"
            )
        ]
    )
    assert resume.user_id == 1
    assert resume.educations[0].school_name == "서울고등학교"
    assert resume.experiences[0].company_name == "회사"

def test_invalid_education_date_format():
    with pytest.raises(ValueError):
        EducationCreate(
            education_type="대학교",
            school_name="서울대",
            education_status="졸업",
            start_date="202001",  # 잘못된 날짜
            end_date="2024/01"     # 잘못된 날짜
        )