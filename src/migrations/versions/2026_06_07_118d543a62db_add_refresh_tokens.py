"""add_refresh_tokens

Revision ID: 118d543a62db
Revises: 58ddda478ac5
Create Date: 2026-06-07 23:35:13.176317

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '118d543a62db'
down_revision: Union[str, Sequence[str], None] = '8ade4219fc90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(),
                  server_default=sa.text('now()'),
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(),
                  server_default=sa.text('now()'),
                  nullable=False),

        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),

        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_refresh_tokens_token',
                    'refresh_tokens', ['token'],
                    unique=False)


def downgrade() -> None:
    op.drop_index('ix_refresh_tokens_token', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
