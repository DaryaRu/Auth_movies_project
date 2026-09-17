"""email change templates

Revision ID: a3f7c1e9b4d6
Revises: db942c0b26f1
Create Date: 2026-09-16

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f7c1e9b4d6"
down_revision: Union[str, Sequence[str], None] = "db942c0b26f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Шаблоны для смены email: код подтверждения на старый адрес и код
    подтверждения на новый адрес."""
    op.execute(
        """
        INSERT INTO templates (code, name, channel, subject, body, allowed_variables)
        VALUES
            ('email_change_code_old', 'Код подтверждения смены email (текущий адрес)', 'email',
             'Запрос на смену привязанного email',
             'С Вашего аккаунта запрошена смена email на {{ new_email }}. Для подтверждения введите код: {{ code }}

Если Вы не запрашивали смену email, проигнорируйте это письмо и смените пароль.',
             '["code", "new_email"]'),
            ('email_change_code_new', 'Код подтверждения смены email (новый адрес)', 'email',
             'Подтверждение нового email',
             'Ваш код подтверждения нового адреса: {{ code }}

Если Вы не запрашивали смену email, проигнорируйте это письмо.',
             '["code"]')
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "DELETE FROM templates WHERE code IN ('email_change_code_old', 'email_change_code_new')"
    )
