from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, cast, Date

from app.models.job_postings import JobPosting
from app.models.job_applications import JobApplication
from app.models.users import User


class JobPostingRepository:
    """채용 공고 데이터베이스 상호작용을 담당하는 레포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, job_posting_data: dict) -> JobPosting:
        """새로운 채용 공고를 데이터베이스에 생성합니다."""
        job_posting = JobPosting(**job_posting_data)
        self.session.add(job_posting)
        await self.session.commit()
        await self.session.refresh(job_posting)
        return job_posting

    async def get_by_id(self, job_posting_id: int) -> JobPosting | None:
        """ID로 특정 채용 공고를 조회합니다."""
        return await self.session.get(JobPosting, job_posting_id)

    async def list_all(self, skip: int, limit: int) -> List[JobPosting]:
        """모든 채용 공고 목록을 페이지네이션하여 조회합니다 (최신순)."""
        query = (
            select(JobPosting)
            .order_by(desc(JobPosting.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_all(self) -> int:
        """전체 채용 공고 개수를 조회합니다."""
        query = select(func.count(JobPosting.id))
        return await self.session.scalar(query) or 0

    async def update(self, job_posting_id: int, update_data: Dict[str, Any]) -> JobPosting | None:
        """기존 채용 공고를 업데이트합니다."""
        job_posting = await self.get_by_id(job_posting_id)
        if not job_posting:
            return None

        if not update_data:
            return job_posting

        for key, value in update_data.items():
            setattr(job_posting, key, value)

        await self.session.commit()
        await self.session.refresh(job_posting)
        return job_posting

    async def delete(self, job_posting_id: int) -> bool:
        """ID로 특정 채용 공고를 삭제합니다. 성공 시 True, 대상 없음 시 False 반환."""
        job_posting = await self.get_by_id(job_posting_id)
        if not job_posting:
            return False

        await self.session.delete(job_posting)
        await self.session.commit()
        return True

    async def search(
        self,
        filters: List,
        order_by_clause: Any,
        skip: int,
        limit: int
    ) -> List[JobPosting]:
        """필터링, 정렬, 페이지네이션을 적용하여 채용 공고를 검색합니다."""
        query = select(JobPosting)
        if filters:
            query = query.where(*filters)

        query = query.order_by(order_by_clause).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_search(self, filters: List) -> int:
        """필터링된 채용 공고의 전체 개수를 계산합니다."""
        base_query = select(JobPosting)
        if filters:
            base_query = base_query.where(*filters)

        count_query = select(func.count()).select_from(base_query.subquery())
        return await self.session.scalar(count_query) or 0

    async def list_popular(self, limit: int) -> List[JobPosting]:
        """지원자 수 기준으로 인기 채용 공고 목록을 조회합니다."""
        # 지원자 수를 계산하는 서브쿼리
        applications_count_sq = (
            select(
                JobApplication.job_posting_id,
                func.count().label('app_count')
            )
            .group_by(JobApplication.job_posting_id)
            .subquery('app_counts')
        )

        # 공고와 지원자 수 서브쿼리 조인 (지원자 없는 공고 포함)
        query = (
            select(JobPosting)
            .outerjoin(applications_count_sq, JobPosting.id == applications_count_sq.c.job_posting_id)
            # 지원자 수 내림차순, 같으면 최신순 정렬 (coalesce로 NULL 처리)
            .order_by(desc(func.coalesce(applications_count_sq.c.app_count, 0)), desc(JobPosting.created_at))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_popular_by_age_group(self, age_start: int, age_end: int, limit: int) -> List[JobPosting]:
        """특정 연령대 지원자 수 기준으로 인기 채용 공고 목록을 조회합니다."""
        # User.birthday(문자열)를 Date로 캐스팅하여 나이 계산
        age_expr = func.floor(
            (func.current_date() - cast(User.birthday, Date)) / 365.25
        )

        # 특정 연령대 지원자 수를 계산하는 서브쿼리
        applications_count_sq = (
            select(
                JobApplication.job_posting_id,
                func.count().label('app_count')
            )
            .join(User, User.id == JobApplication.user_id)
            .where(
                age_expr >= age_start,
                age_expr < age_end
            )
            .group_by(JobApplication.job_posting_id)
            .subquery()
        )

        # 공고와 연령대별 지원자 수 서브쿼리 조인 (지원자 있는 공고만 포함)
        query = (
            select(JobPosting)
            .join(applications_count_sq, JobPosting.id == applications_count_sq.c.job_posting_id)
            .order_by(desc(applications_count_sq.c.app_count), desc(JobPosting.created_at))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_favorited_posting_ids(self, user_id: int, posting_ids: List[int]) -> set[int]:
        """주어진 공고 ID 목록 중 사용자가 즐겨찾기한 공고 ID들을 반환합니다."""
        # 순환 참조 방지를 위해 함수 내에서 Favorite 모델 import
        from app.models.favorites import Favorite
        if not posting_ids:
            return set()

        favorite_query = select(Favorite.job_posting_id).where(
            and_(
                Favorite.user_id == user_id,
                Favorite.job_posting_id.in_(posting_ids)
            )
        )
        favorite_result = await self.session.execute(favorite_query)
        return {row[0] for row in favorite_result} 