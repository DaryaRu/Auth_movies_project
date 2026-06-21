"""add_oauth_accounts

Revision ID: eef1a67d3a14
Revises: 58b41ae859b2
Create Date: 2026-06-20 21:36:06.763805

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'eef1a67d3a14'
down_revision: Union[str, Sequence[str], None] = '58b41ae859b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE oauth_accounts (
        id UUID NOT NULL,
        user_id UUID NOT NULL,
        provider TEXT NOT NULL,
        provider_user_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (id, provider),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) PARTITION BY LIST (provider);
    """)

    op.create_index(
        'ix_oauth_accounts_provider_provider_user_id',
        'oauth_accounts',
        ['provider', 'provider_user_id'],
        unique=True
    )

    op.execute("""
    CREATE TABLE oauth_accounts_google
    PARTITION OF oauth_accounts
    FOR VALUES IN ('google');
    """)

    op.execute("""
    CREATE TABLE oauth_accounts_yandex
    PARTITION OF oauth_accounts
    FOR VALUES IN ('yandex');
    """)

    op.execute("""
    CREATE TABLE oauth_accounts_vk
    PARTITION OF oauth_accounts
    FOR VALUES IN ('vk');
    """)


def downgrade() -> None:
    op.drop_index(
        'ix_oauth_accounts_provider_provider_user_id',
        table_name='oauth_accounts'
    )

    op.execute("DROP TABLE oauth_accounts_google;")
    op.execute("DROP TABLE oauth_accounts_yandex;")
    op.execute("DROP TABLE oauth_accounts_vk;")
    op.execute("DROP TABLE oauth_accounts;")
