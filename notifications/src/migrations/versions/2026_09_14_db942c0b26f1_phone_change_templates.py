"""phone change templates

Revision ID: db942c0b26f1
Revises: 0c969fe569e4
Create Date: 2026-09-14

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "db942c0b26f1"
down_revision: Union[str, Sequence[str], None] = "0c969fe569e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Шаблоны для смены номера телефона: код подтверждения на email и
    финальное уведомление о смене."""
    op.execute(
        """
        INSERT INTO templates (code, name, channel, subject, body, allowed_variables)
        VALUES
            ('phone_change_code', 'Код подтверждения смены номера (email)', 'email',
             'Код подтверждения смены номера телефона',
             'Для смены номера телефона на Вашем аккаунте введите этот код: {{ code }}

Если Вы не запрашивали смену номера, проигнорируйте это письмо.',
             '["code"]'),
            ('phone_changed', 'Смена номера телефона (email)', 'email',
             'Номер телефона был изменен',
             'Номер телефона Вашего аккаунта был изменен. Если это были не Вы, обратитесь в службу поддержки.',
             '[]')
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "DELETE FROM templates WHERE code IN ('phone_change_code', 'phone_changed')"
    )
