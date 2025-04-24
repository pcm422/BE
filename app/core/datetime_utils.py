from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    import pytz
    ZoneInfo = pytz.timezone

KST = ZoneInfo("Asia/Seoul")
UTC = timezone.utc

def get_now_utc() -> datetime:
    """현재 시각을 UTC로 반환합니다."""
    return datetime.now(UTC)

def to_kst(dt: datetime) -> datetime:
    """datetime 객체를 KST로 변환합니다."""
    return dt.astimezone(KST)