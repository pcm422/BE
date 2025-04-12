from datetime import datetime, timedelta

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import Interest, User, UserInterest

from .schemas import (PasswordReset, TokenRefreshRequest, UserLogin,
                      UserProfileUpdate, UserRegister)
from ...core.config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, REFRESH_TOKEN_EXPIRE_MINUTES

load_dotenv()


def get_password_hash(password: str) -> str:
    # bcrypt 라이브러리를 직접 사용하여 해시
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt.hashpw로 검증
    return bcrypt.hashpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8")).decode("utf-8") == hashed_password


# JWT 토큰 생성 함수들
async def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    # 액세스 토큰을 생성하는 비동기 함수
    to_encode = data.copy()  # 인코딩할 데이터를 복사
    if expires_delta:
        expire = (
            datetime.now() + expires_delta
        )  # 주어진 만료기간을 이용하여 만료 시각 계산
    else:
        expire = datetime.now() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )  # 기본 만료 시간 설정
    to_encode.update({"exp": expire})  # 만료 정보 추가
    encoded_jwt = jwt.encode(
        to_encode, SECRET_KEY, algorithm=ALGORITHM
    )  # JWT 토큰 생성
    return encoded_jwt  # 생성된 토큰 반환


async def create_refresh_token(data: dict) -> str:
    # 리프레쉬 토큰을 생성하는 비동기 함수
    expire = datetime.now() + timedelta(
        minutes=REFRESH_TOKEN_EXPIRE_MINUTES
    )  # 리프레쉬 토큰 만료시간 계산
    data.update({"exp": expire})  # 만료 정보 추가
    encoded_jwt = jwt.encode(
        data, SECRET_KEY, algorithm=ALGORITHM
    )  # 리프레쉬 토큰 생성
    return encoded_jwt  # 생성된 토큰 반환


# 사용자 등록 기능
async def register_user(db: AsyncSession, user_data: UserRegister) -> dict:
    # DB에서 중복 이메일 확인을 위한 쿼리를 실행
    result = await db.execute(
        select(User).filter(User.email == user_data.email)
    )  # 이메일로 사용자 검색
    existing_user = result.scalar_one_or_none()  # 결과에서 하나 또는 None 반환
    if existing_user:
        # 중복 이메일 존재 시 예외 발생
        raise HTTPException(status_code=409, detail="이미 존재하는 이메일입니다.")
    # 새로운 User 인스턴스 생성 (비밀번호는 해시 처리)
    new_user = User(
        name=user_data.name,  # 이름 할당
        email=user_data.email,  # 이메일 할당
        password=get_password_hash(user_data.password),  # 비밀번호 해시 후 할당
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
    }  # 90


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
    user = result.scalar_one_or_none()  # 사용자 객체 또는 None 반환
    if not user:
        raise HTTPException(status_code=404, detail="유저가 조회되지 않습니다.")

    # 각 필드 업데이트
    if update_data.name is not None:
        user.name = update_data.name  # 이름 업데이트
    if update_data.password is not None:
        user.password = get_password_hash(
            update_data.password
        )  # 비밀번호 해시 후 업데이트
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

    await db.commit()  # 사용자 정보 업데이트 커밋
    await db.refresh(user)  # 사용자 최신 정보 갱신
    user = result.unique().scalar_one()

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
        raise HTTPException(status_code=403, detail="자신의 회원탈퇴만 가능한다.")
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
        # 관심분야의 이름 리스트
        "interests": [ui.interest.name for ui in user.user_interests],
        "signup_purpose": user.signup_purpose,
        "referral_source": user.referral_source,
        "user_image": user.user_image,
        "created_at": user.created_at.isoformat(),
    }
    return {"status": "success", "data": response_data}


# 비밀번호 재설정 기능
async def reset_password(db: AsyncSession, data: PasswordReset) -> dict:
    # 이메일과 이름으로 사용자 검색
    result = await db.execute(
        select(User).filter(User.email == data.email, User.name == data.name)
    )  # 쿼리 실행
    user = result.scalar_one_or_none()  # 사용자 객체 반환
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    # 새로운 비밀번호 해시 처리 후 업데이트
    user.password = get_password_hash(data.new_password)  # 176
    await db.commit()  # 변경사항 커밋
    return {"status": "success", "message": "비밀번호가 재설정되었습니다."}  # 결과 반환


# 관심분야 기반 추천 채용공고 제공 기능
async def recommend_jobs(db: AsyncSession, current_user: User) -> dict:
    # 사용자의 관심분야 추출
    user_interests = [ui.interest.name for ui in current_user.user_interests]

    # DB에서 관심분야에 해당하는 채용공고 검색
    from app.models import JobPosting  # JobPosting 모델 import 필요
    result = await db.execute(
        select(JobPosting).filter(JobPosting.job_category.in_(user_interests))
    )
    job_postings = result.scalars().all()

    if not job_postings:
        raise HTTPException(status_code=404, detail="해당 채용정보를 찾을 수 없습니다.")

    # 직렬화된 응답 데이터 구성
    job_list = [
        {
            "job_id": job.id,
            "title": job.title,
            "industry": job.job_category,
            "company": job.work_place_name,
            "location": job.work_address,
            "deadline": job.deadline_at.isoformat() if job.deadline_at else None,
        }
        for job in job_postings
    ]

    return {"status": "success", "data": job_list}


# 이메일로 사용자 조회 함수 (외부 참조용)
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    # 이메일을 기준으로 사용자를 조회하는 함수
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalar_one_or_none()
