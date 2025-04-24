from fastapi import FastAPI
from sqladmin import Admin, ModelView
from app.core.db import engine
from app.models.company_info import CompanyInfo
from app.models.company_users import CompanyUser
from app.models.interests import Interest
from app.models.job_applications import JobApplication
from app.models.resumes import Resume
from app.models.resumes_educations import ResumeEducation
from app.models.users import User
from app.models.job_postings import JobPosting
from app.models.favorites import Favorite
from app.models.admin_users import AdminUser
from app.admin.auth import AdminAuth
from app.core.config import SECRET_KEY
from app.models.users_interests import UserInterest
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.core.db import AsyncSessionFactory
from app.models.job_experience import ResumeExperience
import bcrypt
import datetime
from zoneinfo import ZoneInfo

# 한국 시간대 정의
KST = ZoneInfo("Asia/Seoul")

def format_datetime_kst(model, name: str) -> str:
    """datetime 객체의 시간 값은 유지하고 시간대만 KST로 표시합니다.
       date 객체는 YYYY-MM-DD 형식으로 포맷합니다.
    """
    value = getattr(model, name, None)
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        return value.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    elif isinstance(value, datetime.date):
         return value.strftime("%Y-%m-%d")
    return str(value)

# 비밀번호 암호화 믹스인 클래스
class PasswordHashMixin:
    async def insert_model(self, request, data):
        # 비밀번호 암호화
        if "password" in data and data["password"] and not self._is_hashed(data["password"]):
            password_bytes = data["password"].encode('utf-8')
            hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
            data["password"] = hashed.decode('utf-8')

        # 부모 클래스의 insert_model 메서드 호출
        return await super().insert_model(request, data)

    async def update_model(self, request, pk, data):
        # 비밀번호 암호화
        if "password" in data and data["password"] and not self._is_hashed(data["password"]):
            password_bytes = data["password"].encode('utf-8')
            hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
            data["password"] = hashed.decode('utf-8')

        # 부모 클래스의 update_model 메서드 호출
        return await super().update_model(request, pk, data)

    def _is_hashed(self, password):
        # 이미 해싱된 비밀번호인지 확인
        return password.startswith("$2b$") or password.startswith("$2a$")

# 슈퍼유저 접근 권한 Mixin 클래스
class SuperuserAccessMixin:
    def is_accessible(self, request) -> bool:
        user = getattr(request.state, "user", None)
        return user and user.is_superuser

    def has_create_permission(self, request) -> bool:
        user = getattr(request.state, "user", None)
        return user and user.is_superuser

    def has_update_permission(self, request) -> bool:
        user = getattr(request.state, "user", None)
        return user and user.is_superuser

    def has_delete_permission(self, request) -> bool:
        user = getattr(request.state, "user", None)
        return user and user.is_superuser

class BaseAdmin(ModelView):
    # 선택적으로 로드할 관계 필드 목록 (기본값은 빈 리스트)
    column_selectinload_list = []

    async def get_list(self):
        async with AsyncSessionFactory() as session:
            stmt = select(self.model)

            # 명시적으로 지정된 관계만 selectinload
            for rel in self.column_selectinload_list:
                stmt = stmt.options(selectinload(rel))

            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_one(self, id):
        async with AsyncSessionFactory() as session:
            stmt = select(self.model).where(self.model.id == id)

            # 명시적으로 지정된 관계만 selectinload
            for rel in self.column_selectinload_list:
                stmt = stmt.options(selectinload(rel))

            result = await session.execute(stmt)
            return result.scalar_one_or_none()

class UserAdmin(PasswordHashMixin, SuperuserAccessMixin, BaseAdmin, model=User):
    column_list = ["id", "name", "email", "phone_number", "is_active", "created_at", "updated_at"]
    column_searchable_list = ["name", "email", "phone_number"]
    column_selectinload_list = [User.favorites, User.applications, User.user_interests]
    name = "회원"
    name_plural = "회원 목록"
    column_labels = {
        "id": "번호",
        "name": "이름",
        "email": "이메일",
        "user_image": "이미지",
        "password": "비밀번호",
        "phone_number": "전화번호",
        "birthday": "생년월일",
        "gender": "성별",
        "signup_purpose": "가입 목적",
        "referral_source": "유입경로",
        "is_active": "이메일 활성상태",
        "created_at": "가입일 (KST)",
        "updated_at": "수정일 (KST)",
        "user_interests": "관심분야"
    }
    column_formatters = {
        "created_at": format_datetime_kst,
        "updated_at": format_datetime_kst,
    }
    column_details_exclude_list = ["password"]

class JobPostingAdmin(BaseAdmin, model=JobPosting):
    column_list = [
        "id",
        "title",
        "summary",
        "company.company_name",
        "author.email",
        "job_category",
        "work_duration",
        "is_work_duration_negotiable",
        "work_days",
        "is_work_days_negotiable",
        "is_schedule_based",
        "work_start_time",
        "work_end_time",
        "is_work_time_negotiable",
        "created_at",
    ]
    column_searchable_list = ["title", "company.company_name", "author.email", "job_category"]
    column_selectinload_list = [JobPosting.author, JobPosting.company]
    name = "공고"
    name_plural = "공고 목록"
    column_labels = {
        "id": "번호",
        "title": "제목",
        "summary": "공고 요약 (선택)",
        "author.email": "담당자 이메일",
        "company.company_name": "회사명",
        "recruit_period_start": "모집 시작일",
        "recruit_period_end": "모집 종료일",
        "is_always_recruiting": "상시 모집",
        "education": "요구 학력",
        "recruit_number": "모집 인원",
        "benefits": "복리 후생",
        "preferred_conditions": "우대 조건",
        "other_conditions": "기타 조건",
        "work_address": "근무지",
        "work_place_name": "근무지명",
        "payment_method": "급여 지급 방법",
        "job_category": "직종",
        "work_duration": "근무 기간",
        "is_work_duration_negotiable": "기간 협의 가능",
        "career": "경력",
        "employment_type": "고용형태",
        "salary": "급여",
        "work_days": "근무요일/스케줄 (선택)",
        "is_work_days_negotiable": "요일 협의 가능",
        "is_schedule_based": "스케줄 근무",
        "work_start_time": "근무 시작 시간",
        "work_end_time": "근무 종료 시간",
        "is_work_time_negotiable": "시간 협의 가능",
        "description": "공고상세내용 (선택)",
        "postings_image": "공고이미지",
        "latitude": "위도",
        "longitude": "경도",
        "created_at": "작성일 (KST)",
        "updated_at": "수정일 (KST)",
        "author": "작성자",
        "company": "회사",
        "favorites": "즐겨찾기",
        "applications": "지원 내역"
    }
    column_formatters = {
        "created_at": format_datetime_kst,
        "updated_at": format_datetime_kst,
    }

class FavoriteAdmin(BaseAdmin, model=Favorite):
    column_list = ["id", "user.email", "job_posting.title", "created_at"]
    column_searchable_list = ["user.email", "job_posting.title"]
    column_selectinload_list = [Favorite.user, Favorite.job_posting]
    name = "즐겨찾기"
    name_plural = "즐겨찾기 목록"
    column_labels = {
        "id": "번호",
        "user_id": "회원 ID (삭제됨)",
        "user.email": "회원 이메일",
        "job_posting_id": "공고 ID (삭제됨)",
        "job_posting.title": "공고 제목",
        "created_at": "작성일 (KST)",
        "user": "회원",
        "job_posting": "공고"
    }
    column_formatters = {
        "created_at": format_datetime_kst,
    }

class AdminUserAdmin(PasswordHashMixin, SuperuserAccessMixin, BaseAdmin, model=AdminUser):
    column_list = ["id", "username", "is_superuser"]
    column_searchable_list = ["username"]
    name = "관리자"
    name_plural = "관리자 목록"
    column_labels = {
        "id": "번호",
        "username": "아이디",
        "password": "비밀번호",
        "is_superuser": "슈퍼유저"
    }
    column_details_exclude_list = ["password"]

class CompanyInfoAdmin(BaseAdmin, model=CompanyInfo):
    column_list = [
        "id",
        "company_name",
        "business_reg_number",
        "ceo_name",
        "address",
        "opening_date",
        "manager_name",
        "manager_phone",
        "manager_email"
    ]
    column_searchable_list = ["company_name", "business_reg_number", "ceo_name"]
    column_selectinload_list = [CompanyInfo.job_postings, CompanyInfo.company_users]
    name = "기업 정보"
    name_plural = "기업 정보 목록"
    column_labels = {
        "id": "번호",
        "company_name": "기업명",
        "business_reg_number": "사업자등록번호",
        "opening_date": "개업일",
        "company_intro": "기업 소개",
        "ceo_name": "대표자 성함",
        "address": "사업장 주소",
        "company_image": "회사 이미지 URL",
        "job_postings": "작성한 공고",
        "company_users": "담당자",
        "manager_name": "담당자 이름",
        "manager_phone": "담당자 전화번호",
        "manager_email": "담당자 이메일"
    }

class CompanyUserAdmin(PasswordHashMixin, SuperuserAccessMixin, BaseAdmin, model=CompanyUser):
    column_list = ["id", "company.company_name", "email", "created_at", "updated_at"]
    column_searchable_list = ["email", "company.company_name"]
    column_selectinload_list = [CompanyUser.company, CompanyUser.job_postings]
    name = "기업 담당자"
    name_plural = "기업 담당자 목록"
    column_labels = {
        "id": "번호",
        "company_id": "기업 ID (삭제됨)",
        "company.company_name": "소속 회사",
        "password": "비밀번호",
        "created_at": "가입일 (KST)",
        "updated_at": "수정일 (KST)",
        "email": "로그인 이메일",
        "company": "소속 회사",
        "job_postings": "작성한 공고"
    }
    column_formatters = {
        "created_at": format_datetime_kst,
        "updated_at": format_datetime_kst,
    }
    column_details_exclude_list = ["password"]

class JobApplicationAdmin(BaseAdmin, model=JobApplication):
    column_list = ["id", "user.email", "job_posting.title", "resume_id", "status", "created_at", "updated_at"]
    column_searchable_list = ["user.email", "job_posting.title", "status"]
    column_selectinload_list = [JobApplication.user, JobApplication.job_posting, JobApplication.resume]
    name = "지원 내역"
    name_plural = "지원 내역 목록"
    column_labels = {
        "id": "번호",
        "user_id": "회원 ID (삭제됨)",
        "user.email": "회원 이메일",
        "job_posting_id": "공고 ID (삭제됨)",
        "job_posting.title": "공고 제목",
        "resume_id": "이력서 ID",
        "status": "상태",
        "created_at": "작성일 (KST)",
        "updated_at": "수정일 (KST)",
        "user": "회원",
        "job_posting": "공고",
        "resume": "이력서"
    }
    column_formatters = {
        "created_at": format_datetime_kst,
        "updated_at": format_datetime_kst,
    }

class ResumeAdmin(BaseAdmin, model=Resume):
    column_list = ["id", "user.email", "resume_image", "desired_area", "introduction", "created_at", "updated_at"]
    column_searchable_list = ["user.email", "desired_area", "introduction"]
    column_selectinload_list = [Resume.user, Resume.educations, Resume.experiences]
    name = "이력서"
    name_plural = "이력서 목록"
    column_labels = {
        "id": "번호",
        "user_id": "회원 ID (삭제됨)",
        "user.email": "회원 이메일",
        "resume_image": "이미지 URL",
        "desired_area": "희망 지역",
        "introduction": "자기소개",
        "created_at": "작성일 (KST)",
        "updated_at": "수정일 (KST)",
        "user": "회원",
        "educations": "학력",
        "experiences": "경력"
    }
    column_formatters = {
        "created_at": format_datetime_kst,
        "updated_at": format_datetime_kst,
    }

class ResumeEducationAdmin(BaseAdmin, model=ResumeEducation):
    column_list = ["id", "resume.id", "education_type", "school_name", "education_status", "start_date", "end_date", "created_at", "updated_at"]
    column_searchable_list = ["school_name", "education_type", "education_status"]
    column_selectinload_list = [ResumeEducation.resume]
    name = "학력"
    name_plural = "학력 목록"
    column_labels = {
        "id": "번호",
        "resumes_id": "이력서 ID (삭제됨)",
        "resume.id": "이력서 ID",
        "education_type": "학력구분",
        "school_name": "학교명",
        "education_status": "학력상태",
        "start_date": "시작일",
        "end_date": "종료일",
        "resume": "이력서",
        "created_at": "작성일 (KST)",
        "updated_at": "수정일 (KST)",
    }
    column_formatters = {
        "created_at": format_datetime_kst,
        "updated_at": format_datetime_kst,
    }

class ResumeExperienceAdmin(BaseAdmin, model=ResumeExperience):
    column_list = ["id", "resume.id", "company_name", "position", "start_date", "end_date", "created_at", "updated_at"]
    column_searchable_list = ["company_name", "position", "description"]
    column_selectinload_list = [ResumeExperience.resume]
    name = "경력사항"
    name_plural = "경력사항 목록"
    column_labels = {
        "id": "번호",
        "resume_id": "이력서 ID (삭제됨)",
        "resume.id": "이력서 ID",
        "company_name": "회사명",
        "position": "직무/직급",
        "start_date": "근무 시작일",
        "end_date": "근무 종료일",
        "description": "상세 업무 내용",
        "created_at": "작성일 (KST)",
        "updated_at": "수정일 (KST)",
        "resume": "이력서"
    }
    column_formatters = {
        "created_at": format_datetime_kst,
        "updated_at": format_datetime_kst,
    }

class InterestAdmin(BaseAdmin, model=Interest):
    column_list = ["id", "code", "name", "is_custom"]
    column_searchable_list = ["name", "code"]
    column_selectinload_list = [Interest.user_interests]
    name = "관심분야"
    name_plural = "관심분야 목록"
    column_labels = {
        "id": "번호",
        "code": "코드",
        "name": "이름",
        "is_custom": "사용자 정의 항목 여부",
        "user_interests": "회원 관심분야"
    }

class UserInterestAdmin(BaseAdmin, model=UserInterest):
    column_list = ["id", "user.email", "interest.name"]
    column_searchable_list = ["user.email", "interest.name"]
    column_selectinload_list = [UserInterest.user, UserInterest.interest]
    name = "회원 관심분야"
    name_plural = "회원 관심분야 목록"
    column_labels = {
        "id": "번호",
        "user_id": "회원 ID (삭제됨)",
        "user.email": "회원 이메일",
        "interest_id": "관심분야 ID (삭제됨)",
        "interest.name": "관심분야 이름",
        "user": "회원",
        "interest": "관심분야"
    }


def setup_admin(app: FastAPI):
    admin = Admin(
        app,
        engine,
        base_url="/admin",
        authentication_backend=AdminAuth(secret_key=SECRET_KEY)
    )
    admin.add_view(AdminUserAdmin)
    admin.add_view(UserAdmin)
    admin.add_view(CompanyUserAdmin)
    admin.add_view(UserInterestAdmin)
    admin.add_view(InterestAdmin)
    admin.add_view(JobPostingAdmin)
    admin.add_view(FavoriteAdmin)
    admin.add_view(CompanyInfoAdmin)
    admin.add_view(JobApplicationAdmin)
    admin.add_view(ResumeAdmin)
    admin.add_view(ResumeEducationAdmin)
    admin.add_view(ResumeExperienceAdmin)