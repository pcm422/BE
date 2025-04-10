"""관심분야 추가 user

Revision ID: 16b235b62e05
Revises: 0eae31e3f836
Create Date: 2025-04-10 04:46:05.405444
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16b235b62e05'
down_revision: Union[str, None] = '0eae31e3f836'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 1. jobinterest_enum 타입 먼저 생성
    jobinterest_enum = sa.Enum(
        'office', 'service', 'tech', 'education', 'public', 'driver', 'etc',
        name='jobinterest_enum'
    )
    jobinterest_enum.create(op.get_bind())

    # 2. interests 컬럼 enum 타입으로 변경
    op.alter_column(
        'users',
        'interests',
        existing_type=sa.TEXT(),
        type_=jobinterest_enum,
        existing_nullable=True,
        postgresql_using="interests::jobinterest_enum"
    )

    # 3. custom_interest 컬럼 추가
    op.add_column('users', sa.Column('custom_interest', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""

    # 1. interests 컬럼 타입 원상복구
    op.alter_column(
        'users',
        'interests',
        existing_type=sa.Enum(
            'office', 'service', 'tech', 'education', 'public', 'driver', 'etc',
            name='jobinterest_enum'
        ),
        type_=sa.TEXT(),
        existing_nullable=True
    )

    # 2. custom_interest 컬럼 삭제
    op.drop_column('users', 'custom_interest')

    # 3. enum 타입 삭제
    sa.Enum(
        'office', 'service', 'tech', 'education', 'public', 'driver', 'etc',
        name='jobinterest_enum'
    ).drop(op.get_bind())
