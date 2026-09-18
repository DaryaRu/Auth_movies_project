"""add is_mandatory flag to templates

Revision ID: c9d8e7f6a5b4
Revises: a3f7c1e9b4d6
Create Date: 2026-09-18

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = "a3f7c1e9b4d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Добавить templates.is_mandatory и пометить обязательные шаблоны.

    Обязательные сообщения безопасности: коды подтверждения и уведомления
    об изменении контактов/пароля. Они доставляются независимо от настроек
    рассылок пользователя — категория определяется на стороне сервера
    (по шаблону), а не вызывающим сервисом.
    """
    op.execute(
        """
        ALTER TABLE templates
        ADD COLUMN is_mandatory BOOLEAN NOT NULL DEFAULT false
        """
    )
    op.execute(
        """
        UPDATE templates SET is_mandatory = true
        WHERE code IN (
            'user_registered',
            'password_changed',
            'phone_change_code',
            'phone_changed',
            'email_change_code_old',
            'email_change_code_new'
        )
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "UPDATE templates SET is_mandatory = false WHERE is_mandatory = true"
    )
    op.execute("ALTER TABLE templates DROP COLUMN is_mandatory")
