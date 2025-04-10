from fastapi import FastAPI
from sqladmin import Admin, ModelView
from app.core.db import engine
from app.models.company_info import CompanyInfo
from app.models.company_users import CompanyUser
from app.models.job_applications import JobApplication
from app.models.resumes import Resume
from app.models.resumes_educations import ResumeEducation
from app.models.users import User
from app.models.job_postings import JobPosting
from app.models.favorites import Favorite
from app.models.admin_users import AdminUser
from app.admin.auth import AdminAuth
from app.core.config import SECRET_KEY

class UserAdmin(ModelView, model=User):
    column_list = User.__table__.columns.keys()

class JobPostingAdmin(ModelView, model=JobPosting):
    column_list = JobPosting.__table__.columns.keys()

class FavoriteAdmin(ModelView, model=Favorite):
    column_list = Favorite.__table__.columns.keys()

class AdminUserAdmin(ModelView, model=AdminUser):
    column_list = AdminUser.__table__.columns.keys()
    
class CompanyInfoAdmin(ModelView, model=CompanyInfo):
    column_list = CompanyInfo.__table__.columns.keys()
    
class CompanyUserAdmin(ModelView, model=CompanyUser):
    column_list = CompanyUser.__table__.columns.keys()
    
class jobApplicationAdmin(ModelView, model=JobApplication):
    column_list = JobApplication.__table__.columns.keys()
    
class ResumeAdmin(ModelView, model=Resume):
    column_list = Resume.__table__.columns.keys()
    
class ResumeEducationAdmin(ModelView, model=ResumeEducation):
    column_list = ResumeEducation.__table__.columns.keys()
    

def setup_admin(app: FastAPI):
    admin = Admin(
        app,
        engine,
        base_url="/admin",
        authentication_backend=AdminAuth(secret_key=SECRET_KEY) 
    )
    admin.add_view(AdminUserAdmin)
    admin.add_view(UserAdmin)
    admin.add_view(JobPostingAdmin)
    admin.add_view(FavoriteAdmin)    
    admin.add_view(CompanyInfoAdmin)
    admin.add_view(CompanyUserAdmin)
    admin.add_view(jobApplicationAdmin)
    admin.add_view(ResumeAdmin)
    admin.add_view(ResumeEducationAdmin)