from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from itsdangerous import URLSafeTimedSerializer
from app.core.config import SITE_URL, SECRET_KEY
from fastapi import BackgroundTasks
from app.core.config import (
    EMAIL_HOST_USER,
    EMAIL_HOST_PASSWORD,
    DEFAULT_FROM_EMAIL,
    EMAIL_PORT,
    EMAIL_HOST,
    EMAIL_USE_SSL
)

serializer = URLSafeTimedSerializer(SECRET_KEY)

# FastAPI-Mail에 필요한 Connection 설정
mail_conf = ConnectionConfig(
    MAIL_USERNAME=EMAIL_HOST_USER,   # 네이버 로그인 계정
    MAIL_PASSWORD=EMAIL_HOST_PASSWORD, # 네이버 로그인 비밀번호
    MAIL_FROM=DEFAULT_FROM_EMAIL,   # 보내는 사람(기본)
    MAIL_PORT=EMAIL_PORT,           # 465
    MAIL_SERVER=EMAIL_HOST,         # smtp.naver.com
    MAIL_STARTTLS=not EMAIL_USE_SSL,     # 465/SSL을 쓰면, TLS=False
    MAIL_SSL_TLS=EMAIL_USE_SSL,         # True
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

fast_mail = FastMail(mail_conf)

async def send_html_email(
    background_tasks: BackgroundTasks,
    to_email: str,
    subject: str,
    html_body: str
) -> None:
    """
    HTML 형식 이메일을 발송하는 예시 함수
    비동기로 동작하나, 함수를 더욱 백그라운드로 돌리려면
    BackgroundTasks를 이용할 수도 있음
    """
    message = MessageSchema(
        subject=subject,
        recipients=[to_email],  # 수신자 목록
        body=html_body,
        subtype="html",         # HTML 형식
    )

    # FastAPI에서 long-running tasks를 백그라운드로 처리하기 위해,
    # FastMail의 send_message를 BackgroundTasks와 함께 사용할 수도 있습니다.
    background_tasks.add_task(fast_mail.send_message, message)
    # 즉시 await로 보내고 싶다면:
    # await fast_mail.send_message(message)


def generate_auth_token(user_id: int) -> str:
    """
    사용자의 ID를 직렬화/서명하여 토큰 생성 (만료시간은 검증 단계에서)
    """
    return serializer.dumps(user_id)

async def send_verification_email(
    background_tasks: BackgroundTasks,
    user_id: int,
    to_email: str,
    token: str
):
    verification_link = f"{SITE_URL}/verify-email?token={token}"
    subject = "이메일 인증 안내"
    html_body = f"""
    <h1>이메일 인증</h1>
    <p>아래 링크를 클릭하여 이메일 인증을 완료해주세요:</p>
    <a href='{verification_link}'>인증하기</a>
    <a>{verification_link}</a>
    """

    # 4) 메일 전송
    await send_html_email(background_tasks, to_email, subject, html_body)
