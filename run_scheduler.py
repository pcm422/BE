import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# 스케줄러가 실행할 작업을 임포트
from app.core.tasks import delete_unverified_users

# 로깅 설정: 기본 정보 레벨 이상으로 로깅하고, 로그 형식을 지정.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # 현재 모듈 이름으로 로거 객체 생성

async def main():
    """비동기 스케줄러를 설정하고 시작합니다."""
    # 비동기 I/O 스케줄러 인스턴스 생성
    scheduler = AsyncIOScheduler()
    logger.info("스케줄러가 초기화되었습니다.")

    # 스케줄러에 작업(job) 추가
    scheduler.add_job(
        delete_unverified_users,       # 실행할 함수 (미인증 사용자 삭제)
        trigger=IntervalTrigger(minutes=1), # 트리거: 1분 간격
        id="delete_unverified_users_job", # 작업 ID
        replace_existing=True         # 동일 ID의 기존 작업이 있으면 대체
    )
    # 어떤 작업이 어떤 트리거로 추가되었는지 로그 기록
    logger.info(f"'{delete_unverified_users.__name__}' 작업이 트리거 '{IntervalTrigger(minutes=1)}'(으)로 추가되었습니다.")

    # 스케줄러 시작 (백그라운드에서 실행됨)
    scheduler.start()
    logger.info("스케줄러가 시작되었습니다. 중단될 때까지 계속 실행됩니다...")

    # 스크립트가 즉시 종료되지 않도록 유지
    try:
        # 이벤트 루프를 무한히 실행 상태로 유지 (실제 작업은 스케줄러가 백그라운드에서 처리)
        while True:
            await asyncio.sleep(3600) # 1시간 동안 대기 (주기적인 확인이 필요하면 더 짧게 설정 가능)
    except (KeyboardInterrupt, SystemExit): # Ctrl+C 또는 시스템 종료 시
        logger.info("스케줄러가 중지되었습니다.")
        scheduler.shutdown() # 스케줄러 정상 종료

# 이 스크립트가 직접 실행될 때 main 함수를 실행
if __name__ == "__main__":
    asyncio.run(main()) # 비동기 main 함수 실행 