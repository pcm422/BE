from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from itsdangerous import URLSafeTimedSerializer
from app.core.config import SITE_URL, SECRET_KEY
from fastapi import BackgroundTasks, HTTPException
from app.core.config import (
    EMAIL_HOST_USER,
    EMAIL_HOST_PASSWORD,
    DEFAULT_FROM_EMAIL,
    EMAIL_PORT,
    EMAIL_HOST,
    EMAIL_USE_SSL
)

serializer = URLSafeTimedSerializer(SECRET_KEY)

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
    """  실제 메일 전송 담당 함수
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

async def send_verification_email(
    background_tasks: BackgroundTasks,
    to_email: str,
    token: str,
    user_type: str
):
    """
    이메일 인증을 위한 메일 작성 및 전송 시키는 함수
    """
    verification_link = f"{SITE_URL}/verify-email?token={token}&user_type={user_type}"
    subject = "이메일 인증 안내"
    logo_url = "https://kr.object.ncloudstorage.com/be-bucket/logo.png"
    secondary_logo_url = "https://kr.object.ncloudstorage.com/be-bucket/%EC%8B%9C%EB%8B%88%EC%96%B4%EB%82%B4%EC%9D%BC.png"
    html_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
        <title>이메일 인증 안내</title>
    </head>
    <body style="margin:0;padding:0;font-family:'Inter',sans-serif;background-color:#f0f0f0;line-height:1.6;">
        <div style="width:100%;max-width:620px;margin:120px auto;background:linear-gradient(145deg,#ffffff,#f5f5f5);border-radius:24px;padding:56px;box-shadow:0px 16px 32px rgba(0,0,0,0.15), 0px 8px 16px rgba(0,0,0,0.08);text-align:center;overflow:hidden;position:relative;">
            <div style="text-align:center;margin-bottom:36px;">
                <div style="display:flex;flex-direction:column;align-items:center;margin-bottom:24px;">
                    <img src="{secondary_logo_url}" alt="시니어내일" style="width:150px;height:80px;opacity:0.8;">
                    <img src="{logo_url}" alt="시니어내일" style="width:200px;height:auto;">
                </div>
                <h1 style="font-size:28px;font-weight:700;background:linear-gradient(90deg,#0F8C3B,#10572A);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:16px;">이메일 주소 확인</h1>
                <p style="font-size:16px;color:#555;margin-bottom:24px;">회원가입을 완료하려면 아래 버튼을 클릭해 이메일 주소를 인증해주세요.</p>
            </div>
            <div style="margin-top:16px;">
                <a href="{verification_link}" style="display:inline-block;padding:16px 36px;background:linear-gradient(145deg,#0F8C3B,#10572A);color:#fff;font-size:16px;font-weight:600;text-decoration:none;border-radius:50px;box-shadow:0px 10px 20px rgba(15,140,59,0.3);margin-bottom:24px;">이메일 인증하기</a>
                <p>또는 아래 링크를 복사하여 브라우저에 붙여넣기:</p>
                <a href="{verification_link}" style="font-size:14px;color:#0F8C3B;text-decoration:none;padding:10px 20px;">{verification_link}</a>
            </div>
        </div>
    </body>
    </html>
    """

    await send_html_email(background_tasks, to_email, subject, html_body)
