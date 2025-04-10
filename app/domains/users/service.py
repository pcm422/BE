from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import bcrypt
import logging
from app.models.users import User
from app.domains.users.schemas import UserCreate, UserUpdate

logger = logging.getLogger(__name__)

async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
    """
    신규 사용자 생성
    """
    try:  # 이메일로 이미 존재하는 사용자가 있는지 조회
        result = await db.execute(select(User).filter(User.email == user_create.email))
        existing_user = result.scalars().first()   # 조회 결과에서 첫 번쨰 사용자 추출
        if existing_user:  # 해당 이메일이 존재하면 예외처리
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 이메일 입니다."
            )
        # 비밀번호 해싱
        hashed_pw = bcrypt.hashpw(
            user_create.password.encode("utf-8"),  # 비밀번호 문자열 utf-8로 변환
            bcrypt.gensalt()
        ).decode("utf-8")  # 문자열 반환
        new_user = User(  # 유저 생성
            name=user_create.name,
            email=user_create.email,
            password=hashed_pw,
            phone_number=user_create.phone_number,
            birthday=user_create.birthday,
            gender=user_create.gender,
            interests=user_create.interests,
            custom_interest=user_create.custom_interest,
            signup_purpose=user_create.signup_purpose,
            referral_source=user_create.referral_source,
            is_active=True
        )
        db.add(new_user)  # 사용자 DB 세션에 추가
        await db.commit()  # 커밋
        await db.refresh(new_user)  # 최신 데이터 반영
        return new_user  # 생성된 유저 반환
    except Exception as e:   # 에러 발생시 DB 롤백 후 에러상태, 메세지 반환
        await db.rollback()
        logger.error(f"Error in create_user: {e}")
        raise HTTPException(status_code=500, detail="사용자 생성에 실패하였습니다.")


async def login_user(db: AsyncSession, email: str, password: str) -> User:
    """
    사용자 로그인: 제공된 이메일과 비밀번호로 사용자를 인증.
    """

    result = await db.execute(select(User).filter(User.email == email))   # 이메일 기준으로 조회
    user = result.scalars().first()   # 첫번째 사용자 가져옴
    if not user:  # 없으면 에러처리
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    if not bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8")):  # 비밀번호 맞지 않으면 에러처리
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 올바르지 않습니다."
        )
    if not user.is_active:  # 활성화 상태 True 아니면 에러처리
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이메일 인증이 필요합니다."
        )
    return user  # 유저 반환


async def get_user_by_id(db: AsyncSession, user_id: int) -> User:
    """
    사용자 ID로 해당 사용자를 조회.
    """
    result = await db.execute(select(User).filter(User.id == user_id))  # 사용자 id로 사용자 조회
    user = result.scalars().first()  # 첫번째 추출
    if not user:  # 없으면 예외처리
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 사용자가 존재하지 않습니다."
        )
    return user  # 유저 반환


async def reset_password(db: AsyncSession, name: str, email: str, new_password: str) -> User:
    """
    비밀번호 재설정: 이름과 이메일로 사용자를 조회한 후, 새 비밀번호를 해싱하여 저장.
    """
    query = select(User).filter(User.name == name, User.email == email)    # 이름과 이메일을 기준으로 사용자 조회
    result = await db.execute(query)  # 조회 결과에서 단일 사용자 객체 반환
    user_obj = result.scalar_one_or_none()
    if not user_obj:  # 없으면 예외처리
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    hashed_pw = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")  # 비밀번호 해시화
    user_obj.password = hashed_pw
    db.add(user_obj)  # 데이터베이스 세션에 추가
    try:
        await db.commit()  # 커밋
        await db.refresh(user_obj)  # 갱신
    except Exception as e:  # 에러시
        await db.rollback()   # 서버 롤백
        logger.error(f"Error in reset_password: {e}")  # 에러 상태코드, 메세지 출력
        raise HTTPException(status_code=500, detail="비밀번호 재설정에 실패하였습니다.")
    return user_obj  # 사용자 반환



async def update_user(db: AsyncSession, user_id: int, user_update: UserUpdate, new_password: str = None) -> User:
    """
    사용자 정보 업데이트
    """
    user = await get_user_by_id(db, user_id)  # 사용자 조회

    # 클라이언트에서 전달된 필드만 추출
    update_data = user_update.dict(exclude_unset=True)

    # 새 비밀번호가 있다면 해싱 처리하여 update_data에 추가
    if new_password:
        import bcrypt  # bcrypt 임포트 (파일 상단에 있을 수도 있음)
        hashed_pw = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        update_data['password'] = hashed_pw

    # 만약 업데이트할 필드가 없다면, DB에 커밋하지 않고 바로 반환
    if not update_data:
        return user

    # 전달받은 업데이트 데이터만 동적으로 user 객체에 반영
    for field, value in update_data.items():
        setattr(user, field, value)

    try:
        await db.commit()       # 커밋
        await db.refresh(user)    # 갱신
    except Exception as e:
        await db.rollback()       # 서버 롤백
        logger.error(f"Error in update_user: {e}")  # 에러 상태코드, 메세지 출력
        raise HTTPException(status_code=500, detail="사용자 정보 업데이트에 실패하였습니다.")
    return user  # 사용자 반환



async def delete_user(db: AsyncSession, user_id: int) -> None:
    """
    지정한 사용자 ID의 계정을 삭제.
    """
    user = await get_user_by_id(db, user_id)  # 사용자 아이디로 조회
    await db.delete(user)  # 삭제
    try:
        await db.commit()  # 커밋
    except Exception as e:  # 에러시
        await db.rollback()  # 서버 롤백
        logger.error(f"Error in delete_user: {e}")  # 상태코드, 메세지 출력
        raise HTTPException(status_code=500, detail="사용자 삭제에 실패하였습니다.")


