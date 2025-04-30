from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.tasks.user_clean import delete_unverified_users

def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        delete_unverified_users,
        trigger=IntervalTrigger(minutes=1),  # 일단 1분마다 비활성 사용자 삭제 검사
        id="delete_unverified_users_job",
        replace_existing=True
    )
    scheduler.start()