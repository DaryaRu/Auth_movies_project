# Реализация сервиса нотификаций

## Защита internal-эндпоинтов (`X-Internal-Secret`)

Часть эндпоинтов предназначена только для вызовов от других сервисов (не от браузера/мобильного клиента) — их защищает общий для всего проекта механизм: заголовок `X-Internal-Secret`, сверяемый с `settings.INTERNAL_SERVICE_SECRET` через `secrets.compare_digest` (`src/api/v1/dependencies.py::verify_internal_secret`, `InternalServiceDep`). Не указан секрет на сервисе, не передан заголовок или значение не совпало — `401 Invalid internal secret`. Один и тот же механизм (свой `dependencies.py` в каждом сервисе, тот же принцип) применен и в `auth-service`, `user_actions-service`, `short_links-service`.

## Персональные уведомления: API → Kafka

API генерирует `deduplication_key` (uuid4) и кладет его в сообщение — воркер использует его для дедупликации при переотправке.

При отправке API отвечает `202` только после того, как Kafka подтвердила запись на все реплики(`send_and_wait` с `acks="all"`(настраивается через `KAFKA_ACKS`)). Буфера на стороне продюсера
нет: либо подтвержденная доставка, либо явная ошибка.

Важно: `acks="all"` сам по себе ничего не гарантирует без правильно настроенных параметров топика — если `min.insync.replicas=1` (dev дефолт), ISR может состоять из одного лидера, и подтверждение "от всех реплик" вырождается в подтверждение от одного лидера, реальной защиты от потери при его падении нет. Появляется только при `min.insync.replicas > 1` (в проде — `KAFKA_MIN_INSYNC_REPLICAS=2`, `KAFKA_REPLICATION_FACTOR=3`).

## Воркер: рендер + реальная отправка (`notifications/worker/`)

Отдельный процесс на `faststream.KafkaBroker`, который читает `notification-ready` (постоянно опрашивает Kafka, и как только приходит новое сообщение, сразу вызывается `handle_ready`).

`handle_ready` выполняет оркестрацию функций:
1. `_parse_message` — валидирует сообщение (`pydantic`). Невалидное просто логируется и подтверждается (ack), ретраить не нужно.
2. `_get_or_create_notification` — идемпотентно создает/находит строку в `notifications` по `deduplication_key`. Если строка уже была и `status` `sent`/`skipped` - уже обработано - `handle_ready` завершается.
3. `_check_deliverable` — производит проверки, помечает `notifications` при отказе:
   - `template.is_active` — шаблона нет или неактивен → `mark_notification_failed`;
   - зарегистрирован ли отправитель для `channel` (сейчас только `email`) → `mark_notification_failed`, если нет;
   - `user_notification_settings` — если нет записи, то трактуется `email`/`push` включены, `sms` — нет; канал выключен → `mark_notification_skipped`.
4. `_render_and_send` — получает `email` через
   `GET /api/v1/internal/users/{user_id}/` у `auth-service` (если нет email, например, регистрация по телефону, — `mark_notification_failed`),
   рендерит `subject`/`body` (Jinja2, `{{ var }}`, `StrictUndefined` — не хватает переменной в `payload` → исключение),
   отправляет через `EmailSender` (SMTP, dev — Mailpit, `localhost:8025`),
   `mark_notification_sent`.

Выбрано `ack_policy=AckPolicy.NACK_ON_ERROR` у `@broker.subscriber`. При успехе оффсет коммитится (ack), при необработанном исключении — nack (`consumer.seek()` назад на оффсет этого же сообщения), то же сообщение будет вычитано повторно.

Ретраится через NACK: ошибки БД, сбой резолва аудитории. Сбой доставки конкретному получателю (`_render_and_send`) через NACK не ретраится, а попадает в DLQ.

Перед NACK — пауза `KAFKA_RETRY_BACKOFF_TIME` (`asyncio.sleep`, фиксированная, не экспоненциальная), иначе при затяжном сбое зависимости консьюмер долбит тот же оффсет retry-циклом без задержки, блокируя всю партицию.

### DLQ (`notification.dlq`)

`_render_and_send` при исключении помечает `notification.status=failed` и публикует в топик `notification.dlq` через `dlq_publisher = broker.publisher(settings.KAFKA_DLQ_TOPIC)` (`faststream.KafkaBroker`) — исключение не пробрасывается дальше, NACK для этого сбоя не срабатывает.

Сообщение в DLQ: `{source_topic, notification_id, message (ReadyMessage целиком), error}`.

Автоматической переотправки из DLQ нет — только для наблюдаемости, повторная отправка вручную.

### `EmailSender`: throttle и circuit breaker (`worker/senders/email.py`)

Защита SMTP от перегрузки:

- **Throttle** — не чаще `EMAIL_MAX_PER_SEC` писем в секунду (фиксированный интервал между отправками, не token bucket).
- **Circuit breaker** — после `SMTP_FAILURE_THRESHOLD` подряд неудачных попыток цепь размыкается на `SMTP_CIRCUIT_COOLDOWN_SEC`: следующие попытки в этот период отклоняются сразу (`CircuitBreakerOpenError`), без реального обращения к `aiosmtplib.send()` — не тратя время на заведомо обреченный коннект, пока SMTP лежит. По истечении cooldown — одна пробная попытка (half-open): успех закрывает цепь и сбрасывает счетчик сбоев, неудача — снова открывает.

**Прод SMTP — Yandex.** `EmailSender.send()` передает в `aiosmtplib.send()` `username`/`password`/`use_tls` из настроек (`SMTP_USERNAME`/`SMTP_PASSWORD`/`SMTP_USE_TLS`, дефолты пустые/`False` — для dev с Mailpit, который аутентификации не требует). Для Yandex: `SMTP_HOST=smtp.yandex.ru`, `SMTP_PORT=465`, `SMTP_USE_TLS=true`, `SMTP_USERNAME` — email отправителя.

## Шаблоны: CRUD и получение по code

Эндпоинты:
- `GET /templates/` — список
- `GET /templates/{id}/` — получение шаблона по ID
- `GET /templates/by-code/{code}/` — получение по `code` (для других сервисов)
- `POST /templates/` — создание (`409` при дублирующемся `code`)
- `PATCH /templates/{id}/` — редактирование (без `code`)

## Проверить, что сообщение доходит до Kafka (без воркера/auth-service)

Проверка API → `notification-ready`, без реальной отправки (что сообщение есть в топике)

1. `make notifications-up` (либо `notifications-db`, `notifications-service`, Kafka).
2. `make notifications-test-request` — находит `template_id` реального шаблона `review_liked` и шлет `POST /api/v1/notifications/` изнутри контейнера `notifications-service`.
3. `make notifications-verify-topic` — слушает `notification-ready` и печатает сообщения. Должно появиться сообщение с тем же `user_id`/`template_id`, что в шаге 2.

## Проверить полный путь (событие → отправка email)

1. `make notifications-up` — поднимает Kafka, БД, `notifications-service`, `notifications-worker`, `auth-service`, `mailpit`, `nginx`.
2. `make notifications-register-test-user` — регистрирует пользователя с уникальным email через `localhost/api/v1/registration/` (nginx → `auth-service`), триггерит `notify_user(..., "user_registered")`.
3. `make notifications-check-status` — смотрит последние строки `notifications`. Ожидается `status=sent`, `delivery_address` = email из шага 2.
4. Открыть `http://localhost:8025` (Mailpit) — письмо должно быть в списке.
5. `make notifications-worker-logs` — проверить логи.
6. `make notifications-down`.
