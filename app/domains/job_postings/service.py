from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from sqlalchemy.orm import selectinload

from app.domains.job_postings.schemas import JobPostingCreate, JobPostingUpdate, JobPostingCreateWithImage
from app.models.job_postings import JobPosting
from app.core.utils import upload_image_to_ncp
from fastapi import UploadFile


async def create_job_posting(
    session: AsyncSession, data: JobPostingCreateWithImage, author_id: int, company_id: int, image_file: UploadFile = None
) -> JobPosting:
    # 이미지 업로드 (있을 경우)
    image_url = None
    if image_file:
        image_url = await upload_image_to_ncp(image_file, folder="job_postings")
    
    # data에서 author_id와 company_id를 제외한 데이터 추출
    data_dict = data.model_dump(exclude={"author_id", "company_id"})
    
    # 문자열 필드를 적절한 타입으로 변환
    if "recruit_number" in data_dict and data_dict["recruit_number"] is not None:
        try:
            data_dict["recruit_number"] = int(data_dict["recruit_number"])
        except (ValueError, TypeError):
            data_dict["recruit_number"] = 0  # 변환 불가능한 경우 기본값 설정
    
    if "salary" in data_dict and data_dict["salary"] is not None:
        try:
            data_dict["salary"] = int(data_dict["salary"])
        except (ValueError, TypeError):
            data_dict["salary"] = 0  # 변환 불가능한 경우 기본값 설정
    
    # Enum 타입에 대한 처리 (문자열을 실제 Enum 값으로 변환)
    from app.models.job_postings import JobCategoryEnum, WorkDurationEnum, EducationEnum, PaymentMethodEnum
    
    # 각 Enum 필드 처리
    enum_mappings = {
        "education": EducationEnum,
        "payment_method": PaymentMethodEnum,
        "job_category": JobCategoryEnum,
        "work_duration": WorkDurationEnum
    }
    
    for field, enum_class in enum_mappings.items():
        if field in data_dict and data_dict[field] is not None:
            # 문자열 값이 Enum에 존재하는지 확인
            try:
                # 값이 Enum 멤버 이름과 일치하는 경우 (enum.name)
                data_dict[field] = enum_class[data_dict[field]]
            except (KeyError, ValueError):
                try:
                    # 값이 Enum 값과 일치하는 경우 (enum.value)
                    for enum_member in enum_class:
                        if enum_member.value == data_dict[field]:
                            data_dict[field] = enum_member
                            break
                    else:  # for-else 구문: for 루프가 break 없이 끝나면 실행
                        # 일치하는 Enum 값을 찾지 못한 경우
                        print(f"Warning: Invalid {field} value: {data_dict[field]}")
                        data_dict[field] = list(enum_class)[0]  # 첫 번째 값으로 기본 설정
                except Exception as e:
                    print(f"Error converting {field}: {e}")
                    data_dict[field] = list(enum_class)[0]  # 첫 번째 값으로 기본 설정
    
    # 날짜 형식 확인 및 처리 (이미 처리되어 있을 수 있음)
    date_fields = ["recruit_period_start", "recruit_period_end", "deadline_at"]
    for field in date_fields:
        if field in data_dict and isinstance(data_dict[field], str):
            try:
                from datetime import datetime
                data_dict[field] = datetime.fromisoformat(data_dict[field]).date()
            except (ValueError, TypeError) as e:
                print(f"Error converting date field {field}: {e}")
                data_dict[field] = None
    
    # 새 JobPosting 객체 생성
    job_posting = JobPosting(
        **data_dict, 
        author_id=author_id, 
        company_id=company_id, 
        posings_image=image_url
    )
    
    session.add(job_posting)
    await session.commit()
    await session.refresh(job_posting)
    return job_posting


async def list_job_postings(
    session: AsyncSession, skip: int = 0, limit: int = 10
) -> tuple[list[JobPosting], int]:
    # 목록 조회에 필요한 필드만 선택 (성능 최적화)
    list_columns = [
        JobPosting.id,
        JobPosting.title,
        JobPosting.job_category,
        JobPosting.work_address,
        JobPosting.salary,
        JobPosting.recruit_period_start,
        JobPosting.recruit_period_end,
        JobPosting.deadline_at,
        JobPosting.is_always_recruiting,
        JobPosting.created_at,
        JobPosting.updated_at,
        JobPosting.author_id,
        JobPosting.company_id,
    ]
    
    # 검색 조건이 없는 기본 쿼리
    base_query = select(*list_columns).select_from(JobPosting)
    
    # 카운트 쿼리 (위치 평가식을 사용하여 카운트)
    count_query = select(func.count(1)).select_from(JobPosting)
    
    # 카운트 실행 (최적화된 카운트 쿼리)
    total_count = await session.scalar(count_query)
    
    # 정렬 및 페이지네이션 적용
    query = base_query.order_by(desc(JobPosting.created_at)).offset(skip).limit(limit)
    
    # 최종 쿼리 실행
    result = await session.execute(query)
    
    # 결과 반환 (성능을 위해 목록 조회에 필요한 필드만 포함)
    return list(result.all()), total_count


async def get_job_posting(
    session: AsyncSession, job_posting_id: int
) -> JobPosting | None:
    # 상세 조회는 전체 필드를 가져오되, 캐시를 활용하기 위한 옵션 추가
    result = await session.execute(
        select(JobPosting)
        .where(JobPosting.id == job_posting_id)
        .execution_options(populate_existing=True)
    )
    return result.scalars().first()


async def update_job_posting(
    session: AsyncSession, job_posting_id: int, data: JobPostingUpdate
) -> JobPosting | None:
    # 최적화: 단일 쿼리로 데이터 가져오기
    job_posting = await get_job_posting(session, job_posting_id)
    if not job_posting:
        return None

    # 변경된 필드만 업데이트하여 DB 부하 최소화
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:  # 업데이트할 데이터가 없으면 조기 반환
        return job_posting
        
    for key, value in update_data.items():
        setattr(job_posting, key, value)

    # 트랜잭션 최적화
    await session.commit()
    await session.refresh(job_posting)
    return job_posting


async def delete_job_posting(
    session: AsyncSession, job_posting_id: int
) -> JobPosting | None:
    # 기존 get_job_posting 함수 재사용
    job_posting = await get_job_posting(session, job_posting_id)
    if not job_posting:
        return None

    await session.delete(job_posting)
    await session.commit()
    return job_posting


async def search_job_postings(
    session: AsyncSession,
    keyword: str | None = None,
    location: str | None = None,
    job_category: str | None = None,
    employment_type: str | None = None,
    is_always_recruiting: bool | None = None,
    page: int = 1,
    limit: int = 10,
    sort: str = "latest"
) -> tuple[list[JobPosting], int]:
    # 목록 조회에 필요한 필드만 선택 (성능 최적화)
    list_columns = [
        JobPosting.id,
        JobPosting.title,
        JobPosting.job_category,
        JobPosting.work_address,
        JobPosting.salary,
        JobPosting.recruit_period_start,
        JobPosting.recruit_period_end,
        JobPosting.deadline_at,
        JobPosting.is_always_recruiting,
        JobPosting.created_at,
        JobPosting.updated_at,
        JobPosting.author_id,
        JobPosting.company_id,
    ]
    
    # 기본 쿼리
    base_query = select(*list_columns).select_from(JobPosting)
    
    # 검색 조건 적용
    if keyword:
        base_query = base_query.where(
            JobPosting.title.ilike(f"%{keyword}%") | 
            JobPosting.description.ilike(f"%{keyword}%")
        )
    
    if location:
        base_query = base_query.where(JobPosting.work_address.ilike(f"%{location}%"))
    
    if job_category:
        base_query = base_query.where(JobPosting.job_category == job_category)
    
    if employment_type:
        base_query = base_query.where(JobPosting.employment_type == employment_type)
    
    if is_always_recruiting is not None:
        base_query = base_query.where(JobPosting.is_always_recruiting == is_always_recruiting)
    
    # 카운트 쿼리 (동일한 필터 적용)
    count_query = select(func.count(1)).select_from(
        base_query.alias("filtered_postings")
    )
    
    # 정렬 적용
    if sort == "latest":
        base_query = base_query.order_by(desc(JobPosting.created_at))
    elif sort == "deadline":
        base_query = base_query.order_by(JobPosting.deadline_at)
    elif sort == "salary_high":
        base_query = base_query.order_by(desc(JobPosting.salary))
    elif sort == "salary_low":
        base_query = base_query.order_by(JobPosting.salary)
    
    # 페이지네이션 적용
    skip = (page - 1) * limit
    base_query = base_query.offset(skip).limit(limit)
    
    # 쿼리 실행
    result = await session.execute(base_query)
    total_count = await session.scalar(count_query)
    
    # 결과 반환
    return list(result.all()), total_count
