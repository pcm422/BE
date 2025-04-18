import os
from email.message import EmailMessage
from typing import Optional
import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import (
    EMAIL_HOST, EMAIL_PORT, EMAIL_USE_SSL,
    EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL
)

# 템플릿 로더: 프로젝트 루트 기준으로 app/templates 디렉터리 사용
jinja_env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    autoescape=select_autoescape(["html", "xml"])
)

async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> None:
    if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
        raise RuntimeError("SMTP 인증 정보가 올바르게 설정되지 않았습니다.")

    msg = EmailMessage()
    msg["From"]    = DEFAULT_FROM_EMAIL or EMAIL_HOST_USER
    msg["To"]      = to_email
    msg["Subject"] = subject

    if text_content:
        msg.set_content(text_content)

    msg.add_alternative(html_content, subtype="html")

    await aiosmtplib.send(
        msg,
        hostname=EMAIL_HOST,
        port=EMAIL_PORT,
        username=EMAIL_HOST_USER,
        password=EMAIL_HOST_PASSWORD,
        use_tls=EMAIL_USE_SSL,
    )

