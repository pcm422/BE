from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from fastapi import UploadFile, HTTPException, status

from app.domains.job_postings.schemas import JobPostingUpdate, JobPostingCreate
from app.models.job_postings import JobPosting
from app.models.job_applications import JobApplication
from app.core.utils import upload_image_to_ncp


async def create_job_posting(
    session: AsyncSession,
    job_posting_data: JobPostingCreate,
    author_id: int,
    company_id: int,
    image_file: UploadFile | None = None
) -> JobPosting:
    """채용 공고 생성 (이미지 포함 가능)"""
    image_url = None
    # 이미지 파일이 있으면 업로드 시도
    if image_file:
        try:
            # 이미지 파일명을 고유하게 만들거나 그대로 사용 (utils 함수 정책에 따름)
            image_url = await upload_image_to_ncp(image_file, folder="job_postings")
        except Exception as e:
            # 이미지 업로드 실패 시 로깅 또는 에러 처리
            print(f"Warning: 이미지 업로드 실패 - {e}. 이미지 없이 공고를 생성합니다.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="이미지 업로드 중 오류 발생")

    # JobPostingCreate 모델에서 ORM 모델에 필요한 데이터 추출 (이미지 URL 제외)
    orm_data = job_posting_data.model_dump(exclude={"postings_image"})

    # JobPosting ORM 객체 생성
    job_posting = JobPosting(
        **orm_data,
        author_id=author_id,
        company_id=company_id,
        postings_image=image_url # 업로드된 이미지 URL 또는 None
    )

    try:
        # DB에 추가 및 커밋
        session.add(job_posting)
        await session.commit()
        await session.refresh(job_posting) # DB에서 생성된 정보(ID 등) 포함 객체 갱신
        return job_posting
    except Exception as e:
        # DB 오류 발생 시 롤백 및 예외 발생
        await session.rollback()
        print(f"Error: 채용 공고 생성 중 데이터베이스 오류 발생 - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채용 공고 생성 중 오류가 발생했습니다."
        )


async def list_job_postings(
    session: AsyncSession, skip: int = 0, limit: int = 10
) -> tuple[list[JobPosting], int]:
    """채용 공고 목록 조회 (페이지네이션)"""
    # 전체 개수 조회 쿼리
    count_query = select(func.count(JobPosting.id))
    total_count = await session.scalar(count_query)

    # 공고가 없으면 빈 리스트 반환
    if total_count == 0:
        return [], 0

    # 목록 조회 쿼리 (최신순 정렬)
    list_query = (
        select(JobPosting)
        .order_by(desc(JobPosting.created_at))
        .offset(skip)
        .limit(limit)
    )
    # 쿼리 실행 및 ORM 객체 리스트 가져오기
    result = await session.execute(list_query)
    postings = result.scalars().all()

    # 결과 반환 (공고 리스트, 전체 개수)
    return list(postings), total_count


async def get_job_posting(
    session: AsyncSession, job_posting_id: int
) -> JobPosting | None:
    """ID로 특정 채용 공고 조회"""
    # session.get으로 PK 조회 (없으면 None 반환)
    result = await session.get(JobPosting, job_posting_id, options=[])
    return result


async def update_job_posting(
    session: AsyncSession, job_posting_id: int, data: JobPostingUpdate
) -> JobPosting | None:
    """채용 공고 업데이트"""
    # 수정할 공고 조회 (없으면 None 반환)
    job_posting = await get_job_posting(session, job_posting_id)
    if not job_posting:
        return None

    # 변경된 데이터만 추출 (요청에 명시적으로 포함된 필드만, exclude_unset=True)
    update_data = data.model_dump(exclude_unset=True)

    # 업데이트 할 내용이 없으면 그대로 반환
    if not update_data:
        return job_posting

    # 객체 속성 업데이트
    for key, value in update_data.items():
        setattr(job_posting, key, value)

    try:
        # DB 변경사항 저장
        await session.commit()
        await session.refresh(job_posting) # 변경사항 반영된 객체 갱신
        return job_posting
    except Exception as e:
        # DB 오류 처리
        await session.rollback()
        print(f"Error: 채용 공고 업데이트 중 데이터베이스 오류 발생 - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채용 공고 업데이트 중 오류가 발생했습니다."
        )


async def delete_job_posting(
    session: AsyncSession, job_posting_id: int
) -> None: # 반환 타입을 None으로 변경
    """채용 공고 삭제"""
    # 삭제할 공고 조회
    job_posting = await get_job_posting(session, job_posting_id)
    # 삭제 대상이 없으면 None 반환 (라우터에서 404 처리)
    if not job_posting:
        return None

    try:
        # DB에서 삭제 및 커밋
        await session.delete(job_posting)
        await session.commit()
        return None # 삭제 성공 시 None 반환
    except Exception as e:
        # DB 오류 처리
        await session.rollback()
        print(f"Error: 채용 공고 삭제 중 데이터베이스 오류 발생 - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채용 공고 삭제 중 오류가 발생했습니다."
        )


async def search_job_postings(
    session: AsyncSession,
    keyword: str | None = None,
    location: str | None = None,
    job_category: str | None = None, # Enum 값(value)으로 검색
    employment_type: str | None = None,
    is_always_recruiting: bool | None = None,
    page: int = 1,
    limit: int = 10,
    sort: str = "latest" # 정렬 기준
) -> tuple[list[JobPosting], int]:
    """채용 공고 검색 (필터링, 정렬, 페이지네이션)"""
    # 기본 쿼리 생성
    base_query = select(JobPosting)
    filters = []

    # 검색 조건(필터) 동적 추가
    if keyword:
        filters.append(
            JobPosting.title.ilike(f"%{keyword}%") | # 제목 또는 내용 검색 (OR)
            JobPosting.description.ilike(f"%{keyword}%")
        )
    if location:
        filters.append(JobPosting.work_address.ilike(f"%{location}%"))
    if job_category:
        filters.append(JobPosting.job_category == job_category) # Enum 값으로 정확히 일치
    if employment_type:
        filters.append(JobPosting.employment_type == employment_type)
    if is_always_recruiting is not None:
        filters.append(JobPosting.is_always_recruiting == is_always_recruiting)

    # 필터 적용 (모든 조건 AND)
    if filters:
        base_query = base_query.where(*filters)

    # 필터링된 전체 개수 계산 (서브쿼리 사용)
    count_query = select(func.count()).select_from(base_query.subquery())
    total_count = await session.scalar(count_query)

    # 결과가 없으면 빈 리스트 반환
    if total_count == 0:
        return [], 0

    # 정렬 기준(Clause) 결정
    if sort == "latest":
        order_by_clause = desc(JobPosting.created_at) # 최신순
    elif sort == "deadline":
        order_by_clause = JobPosting.deadline_at # 마감일 오름차순 (가까운 순)
    elif sort == "salary_high":
        order_by_clause = desc(JobPosting.salary) # 급여 내림차순
    elif sort == "salary_low":
        order_by_clause = JobPosting.salary # 급여 오름차순
    else: # 기본 정렬 (최신순)
        order_by_clause = desc(JobPosting.created_at)

    # 페이지네이션 offset 계산
    skip = (page - 1) * limit
    # 최종 목록 쿼리 (정렬, 페이지네이션 적용)
    list_query = base_query.order_by(order_by_clause).offset(skip).limit(limit)

    # 쿼리 실행 및 결과 가져오기
    result = await session.execute(list_query)
    postings = result.scalars().all()

    # 결과 반환 (공고 리스트, 필터링된 전체 개수)
    return list(postings), total_count


async def get_popular_job_postings(
    session: AsyncSession, limit: int = 10
) -> tuple[list[JobPosting], int]:
    """인기 채용 공고 조회 (지원자 수 기준)"""

    # 지원자 수를 계산하는 서브쿼리 생성
    applications_count_sq = (
        select(
            JobApplication.job_posting_id,
            func.count().label('app_count') # 지원자 수 계산
        )
        .group_by(JobApplication.job_posting_id) # 공고 ID 별로 그룹화
        .subquery('app_counts') # 서브쿼리로 사용
    )

    # 채용공고와 지원자 수 서브쿼리 조인 (Outer Join: 지원자 없는 공고도 포함)
    list_query = (
        select(JobPosting)
        .outerjoin(applications_count_sq, JobPosting.id == applications_count_sq.c.job_posting_id)
        # 인기순 정렬: 지원자 수(app_count) 내림차순, 같으면 최신 공고 순
        # coalesce: 지원자 없는 경우(NULL) 0으로 처리하여 정렬
        .order_by(desc(func.coalesce(applications_count_sq.c.app_count, 0)), desc(JobPosting.created_at))
        .limit(limit) # 상위 N개 제한
    )

    # 쿼리 실행 및 결과 가져오기
    result = await session.execute(list_query)
    postings = result.scalars().all()

    # (참고용) 전체 공고 수 계산 - API 응답 스펙에 따라 필요 없을 수 있음
    count_query = select(func.count(JobPosting.id))
    total_count = await session.scalar(count_query)

    # 결과 반환 (인기 공고 리스트, 전체 공고 수)
    return list(postings), total_count