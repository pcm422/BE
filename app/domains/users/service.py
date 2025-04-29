import jwt
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import Interest, User, UserInterest, JobPosting

from .schemas import (TokenRefreshRequest, UserLogin,
                      UserProfileUpdate, UserRegister, PasswordResetverify)
from ..company_users.utiles import verify_password
from ..job_postings.service import _attach_favorite_status
from ...core.config import SECRET_KEY, ALGORITHM
from ...core.utils import hash_password, create_access_token, create_refresh_token

load_dotenv()

async def check_email(db: AsyncSession, email: str) -> dict:
    """이메일 중복 여부를 확인"""
    result = await db.execute(select(User).filter(User.email == email))
    is_duplicate = result.scalar_one_or_none() is not None  # 중복 여부 판단

    return {
        "status": "success",
        "message": "이미 가입된 이메일입니다." if is_duplicate else "회원가입이 가능한 이메일입니다.",
        "is_duplicate": is_duplicate
    }

# 사용자 등록 기능
async def register_user(db: AsyncSession, user_data: UserRegister) -> dict:
    # DB에서 중복 이메일 확인
    email_check_result = await check_email(db, user_data.email)  # 이메일 중복 확인 결과 저장
    if email_check_result["is_duplicate"]:  # 중복된 경우
        return email_check_result  # 이미 가입된 이메일 메시지 반환
    # 새로운 User 인스턴스 생성 (비밀번호는 해시 처리)
    new_user = User(
        name=user_data.name,  # 이름 할당
        email=user_data.email,  # 이메일 할당
        password=hash_password(user_data.password),  # 비밀번호 해시 후 할당
        phone_number=user_data.phone_number,  # 전화번호 할당
        birthday=user_data.birthday,  # 생년월일 할당
        gender=user_data.gender,  # 성별 할당
        signup_purpose=user_data.signup_purpose,  # 가입 목적 할당
        referral_source=user_data.referral_source,  # 유입경로 할당
    )
    db.add(new_user)  # DB 세션에 새 사용자 추가
    await db.commit()  # 변경사항 커밋
    await db.refresh(new_user)  # 최신 사용자 정보 갱신

    # 관심분야 처리
    if user_data.interests:  # 관심분야 데이터가 있을 경우
        for interest_name in user_data.interests:  # 각 관심분야에 대해 반복
            # 기존 관심분야 검색
            result = await db.execute(
                select(Interest).filter(Interest.name == interest_name)
            )  # 해당 이름의 Interest 검색
            interest = result.scalar_one_or_none()  # 결과에서 하나 또는 None 반환
            if not interest:
                # 존재하지 않으면 사용자 정의 관심분야로 새 Interest 생성
                interest = Interest(
                    code=interest_name.lower(), name=interest_name, is_custom=True
                )  # 새 Interest 생성
                db.add(interest)  # 새 Interest 추가
                await db.commit()  # 커밋
                await db.refresh(interest)  # 최신 정보 갱신
            # User와 Interest 간의 연결(UserInterest) 생성
            user_interest = UserInterest(
                user_id=new_user.id, interest_id=interest.id
            )  # 연결 객체 생성
            db.add(user_interest)  # 연결 객체 세션에 추가
        await db.commit()  # 모든 연결 정보 커밋

        result = await db.execute(
            select(User)
            .options(
                selectinload(User.user_interests).selectinload(UserInterest.interest)
            )
            .filter(User.id == new_user.id)
        )
        new_user = result.unique().scalar_one()

    # 응답 데이터 생성 (민감 정보 제외)
    response_data = {
        "id": new_user.id,  # 사용자 ID
        "name": new_user.name,  # 사용자 이름
        "email": new_user.email,  # 이메일
        "gender": new_user.gender,  # 성별
        "birthday": new_user.birthday,  # 생년월일
        "user_image": new_user.user_image,  # 사용자 이미지 URL
        "created_at": new_user.created_at.isoformat(),  # 생성일 (ISO 형식 문자열)
    }
    return {
        "status": "success",
        "message": "회원가입이 완료되었습니다.",
        "data": response_data,
    }  # 최종 결과 반환


# 사용자 로그인 기능
async def login_user(db: AsyncSession, user_data: UserLogin) -> dict:
    # 이메일로 사용자 검색
    result = await db.execute(
        select(User).filter(User.email == user_data.email)
    )  # 사용자 검색 쿼리 실행
    user = result.scalar_one_or_none()  # 결과에서 사용자 객체 또는 None 반환
    if not user:
        # 사용자가 존재하지 않으면 예외 발생
        raise HTTPException(
            status_code=401, detail="이메일 또는 비밀번호가 일치하지 않습니다."
        )
    # 비밀번호 검증
    if not verify_password(
        user_data.password, user.password
    ):  # 비밀번호가 일치하지 않으면
        raise HTTPException(
            status_code=401, detail="이메일 또는 비밀번호가 일치하지 않습니다."
        )
    # JWT 토큰 생성 (사용자 ID를 sub 클레임에 할당)
    access_token = await create_access_token(
        data={"sub": str(user.id)}
    )  # 액세스 토큰 생성
    refresh_token = await create_refresh_token(
        data={"sub": str(user.id)}
    )  # 리프레쉬 토큰 생성
    return {
        "status": "success",
        "message": "로그인에 성공하셨습니다.",
        "data": {
            "accesstoken": access_token,  # 액세스 토큰
            "refreshtoken": refresh_token,  # 리프레쉬 토큰
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
            },  # 사용자 정보
        },
    }

# 사용자 프로필 업데이트 기능
async def update_user(
    db: AsyncSession, user_id: int, update_data: UserProfileUpdate, current_user: User
) -> dict:
    # 본인 확인: 요청된 user_id와 인증된 사용자 ID가 일치하는지 확인
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="자신의 정보만 수정할 수 있습니다.")
    # 사용자 조회
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_interests).selectinload(UserInterest.interest))
        .filter(User.id == user_id)
    )  # 해당 사용자 검색 쿼리
    user = result.unique().scalar_one_or_none()  # 사용자 객체 또는 None 반환
    if not user:
        raise HTTPException(status_code=404, detail="유저가 조회되지 않습니다.")

    # 각 필드 업데이트
    if update_data.name is not None:
        user.name = update_data.name  # 이름 업데이트
    # 비밀번호 변경 로직: 현재 비밀번호 확인 후 새 비밀번호로 변경
    if update_data.password is not None:
        if update_data.current_password is None:
            raise HTTPException(status_code=400, detail="현재 비밀번호를 입력해야 합니다.")
        if not verify_password(update_data.current_password, user.password):
            raise HTTPException(status_code=401, detail="현재 비밀번호가 일치하지 않습니다.")
        user.password = hash_password(update_data.password)  # 새 비밀번호로 업데이트
    if update_data.phone_number is not None:
        user.phone_number = update_data.phone_number  # 전화번호 업데이트
    if update_data.birthday is not None:
        user.birthday = update_data.birthday  # 생년월일 업데이트
    if update_data.gender is not None:
        user.gender = update_data.gender  # 성별 업데이트
    if update_data.signup_purpose is not None:
        user.signup_purpose = update_data.signup_purpose  # 가입 목적 업데이트
    if update_data.referral_source is not None:
        user.referral_source = update_data.referral_source  # 유입경로 업데이트

    # 관심분야 업데이트: interests가 있으면 기존 연결 제거 후 새로 추가
    if update_data.interests is not None:
        user.user_interests.clear()  # 기존 관심분야 연결 제거
        await db.commit()  # 커밋으로 변경사항 반영
        for interest_name in update_data.interests:
            result = await db.execute(
                select(Interest).filter(Interest.name == interest_name)
            )  # 해당 관심분야 검색
            interest = result.scalar_one_or_none()  # 결과 반환
            if not interest:
                interest = Interest(
                    code=interest_name.lower(), name=interest_name, is_custom=True
                )  # 새 관심분야 생성
                db.add(interest)  # DB 세션에 추가
                await db.commit()  # 커밋
                await db.refresh(interest)  # 최신 정보 업데이트
            user_interest = UserInterest(
                user_id=user.id, interest_id=interest.id
            )  # 연결 객체 생성
            db.add(user_interest)  # DB 세션에 추가
        await db.commit()  # 관심분야 업데이트 커밋

    await db.commit()         # 사용자 정보 업데이트 후 최종 커밋
    await db.refresh(user)    # user 객체를 최신 상태로 갱신

    # Lazy loading 방지용 eager loading 재조회
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_interests).selectinload(UserInterest.interest))
        .filter(User.id == user.id)
    )
    user = result.unique().scalar_one()
    # 기존 result 객체를 재사용하는 부분을 제거하여 오류 방지

    response_data = {
        "id": user.id,  # 사용자 ID
        "name": user.name,  # 업데이트된 이름
        "email": user.email,  # 이메일
        "gender": user.gender,  # 성별
        "birthday": user.birthday,  # 생년월일
        "phone_number": user.phone_number,  # 전화번호
        "interests": [
            ui.interest.name for ui in user.user_interests
        ],  # 연결된 관심분야 목록
        "signup_purpose": user.signup_purpose,  # 가입 목적
        "referral_source": user.referral_source,  # 유입경로
        "user_image": user.user_image,  # 사용자 이미지 URL
        "created_at": user.created_at.isoformat(),  # 생성일 (ISO 형식)
    }
    return {"status": "success", "data": response_data}  # 결과 반환


# 회원 탈퇴 기능
async def delete_user(db: AsyncSession, user_id: int, current_user: User) -> dict:
    # 본인 확인
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="자신의 회원탈퇴만 가능합니다.")
    # 사용자 조회
    result = await db.execute(select(User).filter(User.id == user_id))  # 사용자 검색
    user = result.scalar_one_or_none()  # 사용자 객체 반환
    if not user:
        raise HTTPException(status_code=404, detail="유저가 조회되지 않습니다.")
    await db.delete(user)  # 사용자 삭제 요청
    await db.commit()  # 삭제 커밋
    return {
        "status": "success",
        "message": "회원탈퇴가 정상적으로 처리되었습니다.",
    }  # 결과 반환


# 리프레쉬 토큰을 통한 액세스 토큰 재발급 기능
async def refresh_access_token(
    db: AsyncSession, token_data: TokenRefreshRequest
) -> dict:
    try:
        payload = jwt.decode(
            token_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM]
        )  # 리프레쉬 토큰 디코딩
        user_id: str = payload.get("sub")  # 사용자 ID 추출
    except jwt.PyJWTError:
        # 토큰 디코딩 실패 시 예외 발생
        raise HTTPException(
            status_code=401, detail="유효하지 않은 리프레쉬 토큰입니다."
        )
    result = await db.execute(
        select(User).filter(User.id == int(user_id))
    )  # 사용자 검색
    user = result.scalar_one_or_none()  # 결과에서 사용자 객체 반환
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    new_access_token = await create_access_token(
        data={"sub": str(user.id)}
    )  # 새 액세스 토큰 생성
    return {"status": "success", "data": {"accesstoken": new_access_token}}  # 결과 반환


# 사용자 정보 조회 기능
async def get_user_details(db: AsyncSession, user_id: int, current_user: User) -> dict:
    # 본인 확인
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="자신의 정보만 조회할 수 있습니다.")

    # User와 연결된 UserInterest, 그리고 각각의 Interest까지 미리 로드한다.
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_interests).selectinload(UserInterest.interest))
        .filter(User.id == user_id)
    )
    user = result.unique().scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="유저가 조회되지 않습니다.")

    # 응답 데이터 구성 시, 각 user_interest를 순회하며 interest.name을 가져옵니다.
    response_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "gender": user.gender,
        "birthday": user.birthday,
        "phone_number": user.phone_number,
        "interests": [ui.interest.name for ui in user.user_interests],
        "signup_purpose": user.signup_purpose,
        "referral_source": user.referral_source,
        "user_image": user.user_image,
        "created_at": user.created_at.isoformat(),
    }
    return {"status": "success", "data": response_data}


# 비밀번호 재설정 전 사용자 인증
async def verify_user_reset_password(db: AsyncSession, data: PasswordResetverify) -> dict:
    # 이메일, 이름, 전화번호, 생년월일로 사용자 검색
    result = await db.execute(
        select(User).filter(
            and_(
                User.email == data.email,
                User.name == data.name,
                User.phone_number == data.phone_number,
                User.birthday == data.birthday
            )
        )
    )  # 쿼리 실행
    user = result.scalar_one_or_none()  # 사용자 객체 반환
    if not user:
        raise HTTPException(status_code=404, detail="입력한 정보와 일치하는 사용자가 없습니다.")
    return {"status": "success", "data": {"user_id": user.id}}

# 사용자 인증 후 비밀번호 재설정
async def reset_password_after_verification(db: AsyncSession, user_id: int, new_password: str, confirm_password: str) -> dict:
    # 비밀번호와 비밀번호 확인 값이 일치하는지 검증
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="비밀번호와 비밀번호 확인이 일치하지 않습니다.")
    # user_id로 사용자 검색
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="유저가 조회되지 않습니다.")

    # 비밀번호 해시 후 저장
    user.password = hash_password(new_password)
    await db.commit()  # 변경사항 커밋
    return {"status": "success", "message": "비밀번호가 재설정되었습니다."}


# 관심분야 기반 추천 채용공고 제공 기능
async def recommend_jobs(db: AsyncSession, current_user: User) -> dict:
    """관심분야 기반 추천 채용공고 제공 + 즐겨찾기 여부 포함"""
    # 사용자의 관심분야 추출
    user_interests = [ui.interest.name for ui in current_user.user_interests]

    # 관심분야에 해당하는 채용공고 조회
    result = await db.execute(
        select(JobPosting).filter(JobPosting.job_category.in_(user_interests))
    )
    job_postings = result.scalars().all()

    if not job_postings:
        raise HTTPException(status_code=404, detail="해당 채용정보를 찾을 수 없습니다.")

    # 여기서 즐겨찾기 상태 추가
    await _attach_favorite_status(db, job_postings, current_user.id)

    # 최종 직렬화된 응답 데이터
    job_list = [
        {
            "job_id": job.id,  # 공고 ID
            "company_name": job.work_place_name,  # 근무지명
            "title": job.title,  # 제목
            "recruit_period_end": job.recruit_period_end,  # 모집 종료일
            "location": job.work_address,  # 근무 위치
            "is_favorited": job.is_favorited,  # 즐겨찾기 여부
        }
        for job in job_postings
    ]

    return {"status": "success", "data": job_list}

# 이메일로 사용자 조회 함수 (외부 참조용)
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    # 이메일을 기준으로 사용자를 조회하는 함수
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalar_one_or_none()

async def find_my_email_user_info(db: AsyncSession, name: str, phone_number:str, birthday: str) -> dict:
    '''
    이름, 전화번호, 생년월일로 이메일을 찾는 서비스
    '''
    result = await db.execute(
        select(User).filter(
            and_(
            User.name == name,
            User.phone_number == phone_number,
            User.birthday == birthday
            )
        )
    )
    user = result.scalar_one_or_none() #결과

    # 사용자 존재 여부 확인
    if not user:
        raise HTTPException(status_code=404, detail="일치하는 사용자를 찾을수 없습니다.")

    # 이메일 반환
    return {
        "status": "success",
        "data": {"email":user.email}
    }