-- Миграция 001: таблица шаблонов уведомлений.

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
);

CREATE INDEX IF NOT EXISTS idx_templates_code ON templates(code);
CREATE INDEX IF NOT EXISTS idx_templates_channel ON templates(channel);
CREATE INDEX IF NOT EXISTS idx_templates_is_active ON templates(is_active);

-- Базовые шаблоны для персональных уведомлений.
INSERT INTO templates (code, name, channel, subject, body)
VALUES
    ('review_liked', 'Лайк на рецензию (email)', 'email',
     'Вашу рецензию оценили', 'Пользователь поставил лайк на вашу рецензию.'),
    ('review_disliked', 'Дизлайк на рецензию (email)', 'email',
     'Вашу рецензию оценили', 'Пользователь поставил дизлайк на вашу рецензию.'),
    ('user_registered', 'Регистрация пользователя (email)', 'email',
     'Добро пожаловать!', 'Спасибо за регистрацию.'),
    ('password_changed', 'Смена пароля (email)', 'email',
     'Ваш пароль был изменён', 'Пароль Вашего аккаунта был изменён. Если это были не Вы, обратитесь в службу поддержки.')
ON CONFLICT (code) DO NOTHING;
