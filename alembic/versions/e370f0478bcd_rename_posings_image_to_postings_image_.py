"""Rename posings_image to postings_image in job_postings

Revision ID: e370f0478bcd
Revises: e520a121d92a
Create Date: 2025-04-16 14:59:51.680771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# 필요하다면 추가 임포트
# from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e370f0478bcd'
down_revision: Union[str, None] = 'e520a121d92a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### 컬럼 이름 변경으로 수정됨 ###
    op.alter_column(
        'job_postings',             # 테이블 이름
        'posings_image',            # ★ 기존 컬럼명 (오타)
        new_column_name='postings_image', # ★ 새 컬럼명 (정상)
        existing_type=sa.String(length=255),  # ★ 원래 컬럼 타입 (String(255) 맞는지 꼭 확인!)
        existing_nullable=False      # ★ 원래 NULL 허용 여부 (False가 맞는지 꼭 확인!)
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### 컬럼 이름 원복으로 수정됨 ###
    op.alter_column(
        'job_postings',
        'postings_image',           # 현재 컬럼명 (정상)
        new_column_name='posings_image',# ★ 원래 컬럼명 (오타)
        existing_type=sa.String(length=255),  # 타입과 nullable은 upgrade와 동일하게
        existing_nullable=False
    )
    # ### end Alembic commands ###