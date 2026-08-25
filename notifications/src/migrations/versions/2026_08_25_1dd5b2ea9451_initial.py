"""initial

Revision ID: 1dd5b2ea9451
Revises:
Create Date: 2026-08-25

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1dd5b2ea9451'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Таблица шаблонов уведомлений.

    Каждая команда — отдельный op.execute(): asyncpg через SQLAlchemy
    использует extended query protocol и не может выполнить несколько
    команд в одном execute() (в отличие от простого asyncpg.execute()).
    """
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS templates (
            template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            channel VARCHAR(20) NOT NULL CHECK (channel IN ('email', 'sms', 'push')),
            subject TEXT,
            body TEXT NOT NULL,
            -- Список разрешённых переменных (общий для subject и body), например ["user_name", "movie_title"].
            allowed_variables JSONB NOT NULL DEFAULT '[]',
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_templates_code ON templates(code)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_templates_channel ON templates(channel)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_templates_is_active ON templates(is_active)")

    # Базовые шаблоны для персональных уведомлений.
    op.execute(
        """
        INSERT INTO templates (code, name, channel, subject, body)
        VALUES
            ('review_liked', 'Лайк на рецензию (email)', 'email',
             'Вашу рецензию оценили', 'Пользователь поставил лайк на вашу рецензию.'),
            ('review_disliked', 'Дизлайк на рецензию (email)', 'email',
             'Вашу рецензию оценили', 'Пользователь поставил дизлайк на вашу рецензию.'),
            ('user_registered', 'Регистрация пользователя (email)', 'email',
             'Подтвердите ваш email',
             'Добро пожаловать в наш онлайн-кинотеатр!

Пожалуйста, подтвердите ваш email, перейдя по ссылке: {{confirmation_link}}

Если вы не регистрировались у нас, проигнорируйте это письмо.'),
            ('password_changed', 'Смена пароля (email)', 'email',
             'Ваш пароль был изменён', 'Пароль Вашего аккаунта был изменён. Если это были не Вы, обратитесь в службу поддержки.')
        ON CONFLICT (code) DO NOTHING
        """
    )

    # Обновить allowed_variables для user_registered
    op.execute(
        """
        UPDATE templates
        SET allowed_variables = '["user_name", "confirmation_link"]'::jsonb
        WHERE code = 'user_registered'
        """
    )

    # Шаблон для уведомления о выходе новой серии.
    op.execute(
        """
        INSERT INTO templates (code, name, channel, subject, body, allowed_variables)
        VALUES
            ('new_episode', 'Новая серия сериала (email)', 'email',
             'Вышла новая серия «{{ tv_show_title }}»',
             'Сезон {{ season_number }}, серия {{ episode_number }}: «{{ episode_title }}» — уже доступна.',
             '["tv_show_title", "season_number", "episode_number", "episode_title"]')
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS templates")
