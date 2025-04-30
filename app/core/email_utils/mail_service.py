from datetime import datetime, timedelta
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.email_utils.mail_send import send_verification_email
from app.models.users import EmailVerification
from app.core.config import SECRET_KEY

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

serializer = URLSafeTimedSerializer(SECRET_KEY)

# 이메일 인증 요청 처리
async def handle_verification_email(
    background_tasks: BackgroundTasks,
    email: str,
    db: AsyncSession,
    user_type: str
):
    """
    이메일 인증 전체 흐름을 캡슐화한 핵심 함수
    - 토큰 생성
    - 메일 전송
    - email_verifications 테이블에 저장
    """
    try:
        # 토큰 생성 (email -> 서명된 문자열로 변환)
        token = serializer.dumps(email)

        # 인증 이메일 전송
        await send_verification_email(
            background_tasks=background_tasks,
            to_email=email,
            token=token,
            user_type=user_type
        )

        # 인증 요청 정보 DB 저장
        verification = EmailVerification(
            email=email,
            token=token,
            expires_at=datetime.now() + timedelta(minutes=30),
            is_verified=False,
            user_type=user_type
        )
        db.add(verification)
        await db.commit()

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"이메일 인증 메일 전송 실패: {str(e)}")


# 이메일 인증 처리
async def verify_user_email(token: str, db: AsyncSession, user_type: str) -> dict:
    """
    이메일 인증 처리 서비스 함수
    - 토큰 복호화 (email 추출)
    - email_verifications 테이블에서 상태 갱신
    """
    try:
        email = serializer.loads(token, max_age=1800)  # 30분 유효
    except SignatureExpired:
        raise HTTPException(status_code=400, detail="토큰이 만료되었습니다.")
    except BadSignature:
        raise HTTPException(status_code=400, detail="잘못된 인증 토큰입니다.")

    # 인증 요청 정보 조회
    result = await db.execute(
        select(EmailVerification)
        .where(EmailVerification.email == email,
                EmailVerification.user_type == user_type
        )
        .order_by(EmailVerification.expires_at.desc())
        .limit(1)
    )
    verification = result.scalar_one_or_none()

    if not verification:
        raise HTTPException(status_code=404, detail="인증 요청 내역이 없습니다.")

    if verification.is_verified:
        raise HTTPException(status_code=400, detail="이미 인증된 이메일입니다.")

    # 인증 상태 업데이트
    verification.is_verified = True
    await db.commit()

    return {
        "status": "success",
        "message": "이메일 인증이 완료되었습니다. 이제 회원가입을 진행하세요.",
    }