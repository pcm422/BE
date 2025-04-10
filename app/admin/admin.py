from fastapi import FastAPI
from sqladmin import Admin, ModelView
from app.core.db import engine  # SQLAlchemy async engine
from app.models.users import User
from app.models.job_postings import JobPosting
from app.models.favorites import Favorite  # 혹시 있으면

# 1. 모델 뷰 정의
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.name, User.email, User.created_at]

class JobPostingAdmin(ModelView, model=JobPosting):
    column_list = [JobPosting.id, JobPosting.title, JobPosting.salary, JobPosting.deadline_at]

class FavoriteAdmin(ModelView, model=Favorite):
    column_list = [Favorite.id, Favorite.user_id, Favorite.job_posting_id]

# 2. 어드민 등록 함수
def setup_admin(app: FastAPI):
    admin = Admin(app, engine, base_url="/admin")
    admin.add_view(UserAdmin)
    admin.add_view(JobPostingAdmin)
    admin.add_view(FavoriteAdmin)