-- Таблица настроек коротких ссылок (redirect_url настраивается из админки)

CREATE TABLE IF NOT EXISTS settings (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key           VARCHAR(100) NOT NULL UNIQUE,
    value         VARCHAR(2048) NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Значение по умолчанию: главная страница онлайн-кинотеатра
INSERT INTO settings (key, value)
VALUES ('email_confirmation_redirect_url', 'http://localhost/')
ON CONFLICT (key) DO NOTHING;