-- Миграция 004: ручные рассылки из админки (Immediate group / Scheduled group).

CREATE TABLE IF NOT EXISTS admin_mailings (
    admin_mailing_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES templates(template_id),
    -- Уведомляемая аудитория.
    audience_filter JSONB NOT NULL DEFAULT '{}',
    -- Данные для подстановки в шаблон, общие для всех получателей.
    payload JSONB NOT NULL DEFAULT '{}',
    -- Статус всей рассылки целиком.
    --   scheduled — ожидает заданное время scheduled_at;
    --   sending   — сообщение опубликовано в Kafka, воркер начинает рассылку;
    --   sent      — воркер обработал всех получателей и разослал уведомления;
    --   failed    — не удалось обработать рассылку (например, template_id не найден). Ошибки отдельных получателей сюда не попадают.
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('scheduled', 'sending', 'sent', 'failed')),
    -- Когда отправить, если не сразу. NULL — отправка сразу после создания (Immediate group).
    scheduled_at TIMESTAMP WITH TIME ZONE,
    -- Когда рассылка реально завершена (переход в sent). NULL - пока не завершена.
    sent_at TIMESTAMP WITH TIME ZONE,
    -- Админ, создавший рассылку (пользователь auth service).
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- статус scheduled без scheduled_at бессмысленен.
    CHECK (status != 'scheduled' OR scheduled_at IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_admin_mailings_status_scheduled_at ON admin_mailings(status, scheduled_at);
