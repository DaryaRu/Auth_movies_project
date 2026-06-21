"""update_users

Revision ID: 58b41ae859b2
Revises: f3a6c8d26648
Create Date: 2026-06-20 20:45:01.763747

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '58b41ae859b2'
down_revision: Union[str, Sequence[str], None] = 'f3a6c8d26648'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index('ix_users_email_unique', table_name='users')
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)
    op.alter_column('users', 'hashed_password',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)
    op.create_index('ix_users_phone_unique', 'users', ['phone'], unique=True, postgresql_where=sa.text('phone IS NOT NULL'))
    op.create_index('ix_users_email_unique', 'users', ['email'], unique=True, postgresql_where=sa.text('email IS NOT NULL'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_users_phone_unique', table_name='users', postgresql_where=sa.text('phone IS NOT NULL'))
    op.alter_column('users', 'hashed_password',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
    op.drop_column('users', 'phone')
    op.create_index('ix_users_email_unique', 'users', ['email'], unique=True)
