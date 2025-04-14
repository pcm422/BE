"""merge

Revision ID: fd92936457fc
Revises: 25c320f72f4d, ed55e321e784
Create Date: 2025-04-14 02:36:52.449687

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd92936457fc'
down_revision: Union[str, None] = ('25c320f72f4d', 'ed55e321e784')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
