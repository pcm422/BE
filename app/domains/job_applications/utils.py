import os
from email.message import EmailMessage
from typing import Optional
import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import (
    EMAIL_HOST, EMAIL_PORT, EMAIL_USE_SSL,
    EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL
)
from app.models import Resume

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


def build_resume_snapshot(resume: Resume) -> dict:
    return {
        "resume_image": resume.resume_image,
        "desired_area": resume.desired_area,
        "introduction": resume.introduction,
        "educations": [
            {
                "education_type": edu.education_type,
                "school_name": edu.school_name,
                "education_status": edu.education_status,
                "start_date": edu.start_date.isoformat() if edu.start_date else None,
                "end_date": edu.end_date.isoformat() if edu.end_date else None,
            }
            for edu in resume.educations
        ],
        "experiences": [
            {
                "company_name": exp.company_name,
                "position": exp.position,
                "start_date": exp.start_date.isoformat() if exp.start_date else None,
                "end_date": exp.end_date.isoformat() if exp.end_date else None,
                "description": exp.description,
            }
            for exp in resume.experiences
        ],
    }

async def send_resume_email(
    job_title: str,
    applicant: dict,
    resume: dict,
    to_email: str,
) -> None:
    try:
        template = jinja_env.get_template("resume_email.html")
        html = template.render(
            job_title=job_title,
            applicant=applicant,
            resume=resume,
        )
        await send_email(
            to_email=to_email,
            subject=f"[{job_title}] 지원자 이력서",
            html_content=html,
            text_content="지원자 이력서를 확인해주세요.",
        )
    except Exception as e:
        import logging
        logging.warning(f"이메일 전송 실패: {e}")
