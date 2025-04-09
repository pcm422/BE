"""merge heads

Revision ID: e3e108bc1c24
Revises: 9a42a78b1912, faadb81c0c14
Create Date: 2025-04-09 09:15:54.165977

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3e108bc1c24'
down_revision: Union[str, None] = ('9a42a78b1912', 'faadb81c0c14')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
