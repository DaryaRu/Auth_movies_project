-- Создание таблицы коротких ссылок

CREATE TABLE IF NOT EXISTS short_links (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    short_key     VARCHAR(20) NOT NULL UNIQUE,
    user_id       UUID NOT NULL,
    expires_at    TIMESTAMPTZ NOT NULL,
    redirect_url  VARCHAR(2048) NOT NULL,
    is_used       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индекс по short_key для быстрого поиска при переходе
CREATE INDEX IF NOT EXISTS idx_short_links_short_key ON short_links(short_key);

-- Индекс по user_id для поиска ссылок пользователя
CREATE INDEX IF NOT EXISTS idx_short_links_user_id ON short_links(user_id);

-- Индекс по expires_at для очистки просроченных ссылок
CREATE INDEX IF NOT EXISTS idx_short_links_expires_at ON short_links(expires_at);