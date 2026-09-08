"""merge heads

Revision ID: e6d377e2c5d3
Revises: 8105788f98b7, f71bb140c782
Create Date: 2026-09-08 12:07:43.956767

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = 'e6d377e2c5d3'
down_revision: Union[str, Sequence[str], None] = ('8105788f98b7', 'f71bb140c782')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
