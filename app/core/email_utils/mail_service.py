from itsdangerous import BadSignature, SignatureExpired
from app.core.email_utils.mail_send import serializer
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.email_utils.mail_send import send_verification_email
from app.models import User, CompanyUser, company_users
from app.core.email_utils.mail_send import generate_auth_token

async def handle_verification_email(
    background_tasks: BackgroundTasks,
    user_id: int,
    email: str
):
    try:
        token = generate_auth_token(user_id=user_id)
        await send_verification_email(
            background_tasks=background_tasks,
            user_id=user_id,
            to_email=email,
            token=token
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이메일 인증 메일 전송 실패: {str(e)}")

async def verify_user_email(token: str, db: AsyncSession) -> dict:
    """
    이메일 인증 처리 서비스 함수
    - 토큰 복호화
    - 유효성 확인 및 사용자 활성화
    - 만료 시 계정 삭제
    """
    try:
        user_id = serializer.loads(token, max_age=3600)  # 1시간 유효
    except SignatureExpired:
        # 토큰 만료 시, user_id를 복호화할 수 없으므로 삭제 불가
        # 그러나 itsdangerous의 SignatureExpired는 loads에서 user_id를 반환함
        try:
            user_id = serializer.loads(token)
        except Exception:
            user_id = None
        if user_id is not None:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user and not user.is_active:
                await db.delete(user)
                await db.commit()
        raise HTTPException(status_code=400, detail="인증 링크가 만료되어 계정이 삭제되었습니다.")
    except BadSignature:
        raise HTTPException(status_code=400, detail="잘못된 인증 링크입니다.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        # 일반 사용자에 없으면 기업 사용자 조회 시도
        result = await db.execute(select(CompanyUser).where(CompanyUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    if user.is_active:
        raise HTTPException(status_code=400, detail="이미 인증된 계정입니다.")

    if user:
        user.is_active = True
    else:
        company_users.is_active = True

    await db.commit()

    return {
        "status": "success",
        "message": "이메일 인증이 완료되었습니다. 이제 로그인할 수 있습니다.",
    }