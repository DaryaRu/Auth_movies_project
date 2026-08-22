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
     'Подтвердите ваш email', 
     'Добро пожаловать в наш онлайн-кинотеатр! 

Пожалуйста, подтвердите ваш email, перейдя по ссылке: {{confirmation_link}}

Если вы не регистрировались у нас, проигнорируйте это письмо.'),
    ('password_changed', 'Смена пароля (email)', 'email',
     'Ваш пароль был изменён', 'Пароль Вашего аккаунта был изменён. Если это были не Вы, обратитесь в службу поддержки.')
ON CONFLICT (code) DO NOTHING;

-- Обновить allowed_variables для user_registered
UPDATE templates
SET allowed_variables = '["user_name", "confirmation_link"]'::jsonb
WHERE code = 'user_registered';

-- Шаблон для уведомления о выходе новой серии.
INSERT INTO templates (code, name, channel, subject, body, allowed_variables)
VALUES
    ('new_episode', 'Новая серия сериала (email)', 'email',
     'Вышла новая серия «{{ tv_show_title }}»',
     'Сезон {{ season_number }}, серия {{ episode_number }}: «{{ episode_title }}» — уже доступна.',
     '["tv_show_title", "season_number", "episode_number", "episode_title"]')
ON CONFLICT (code) DO NOTHING;
