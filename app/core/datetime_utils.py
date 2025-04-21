from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Python 3.9 미만 또는 zoneinfo 데이터 부재 시
    # pip install pytz tzdata 필요
    import pytz
    ZoneInfo = pytz.timezone # pytz를 ZoneInfo처럼 사용하기 위한 별칭

KST = ZoneInfo("Asia/Seoul")
UTC = timezone.utc

def get_now_kst() -> datetime:
    """현재 시각을 KST로 반환합니다."""
    return datetime.now(KST) 