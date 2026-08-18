# Что реализовано в сервисе нотификаций

## Персональные уведомления: API → Kafka

Эндпоинт `POST /api/v1/notifications/` принимает `{user_id, template_id, payload}`.
Проверяет, что шаблон существует и активен, ключи `payload` — подмножество
`allowed_variables` шаблона. Собирает сообщение (`user_id`, `template_id`, `payload`, `channel`) и публикует в топик `notification-ready`.

API генерирует `deduplication_key` (uuid4) и кладёт его в сообщение — воркер использует его для дедупликации при переотправке.

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

Выбрано `ack_policy=AckPolicy.NACK_ON_ERROR` у `@broker.subscriber`. При успехе оффсет коммитится (ack). Необработанное исключение в `_render_and_send` → `mark_notification_failed` и `raise` → nack
(`consumer.seek()` назад на оффсет этого же сообщения, `faststream/kafka`), оффсет не коммитится сообщение будет вычитано повторно.

**!Доделать:**
- Нет отдельной обработки "недоставляемых" сообщений (DLQ).
- Нет backoff при повторной доставке.
- Полученный `email` не кэшируется.

## `GET /internal/users/{user_id}/` у auth-service (получение email пользователя)

Новый эндпоинт (`auth/src/api/v1/auth.py`) для получения воркером email пользователя по `user_id`. !!! Сейчас без аутентификации, так же как и CRUD эндпоинты для шаблонов.

## Шаблоны: CRUD и получение по code

Таблица `templates`: `template_id` (PK), `code` (уникальный идентификатор), `name` (название для админки), `channel`, `subject`/`body` (текст с плейсхолдерами `{{ var }}`), `allowed_variables`
(jsonb), `is_active`.

Эндпоинты:
- `GET /templates/` — список
- `GET /templates/{id}/` — получение шаблона по ID
- `GET /templates/by-code/{code}/` — получение по `code` (для других сервисов)
- `POST /templates/` — создание (`409` при дублирующемся `code`)
- `PATCH /templates/{id}/` — редактирование (без `code`)

`asyncpg`- соединение регистрирует codec для `jsonb` (`src/db/postgres.py`), 
`allowed_variables` читается и пишется как обычный `list[str]`.

`src/utils/notifications.py` в других сервисах (`auth`, `user_actions`) резолвит `code → template_id` через `GET /templates/by-code/{code}/` и кэширует результат в Redis (TTL `NOTIFICATIONS_TEMPLATE_ID_CACHE_TTL`).

## Реализованные уведомления

Реализованы три события:

- **Лайк/дизлайк на рецензию** (`user_actions`).
- **Регистрация пользователя** (`auth`).
- **Смена пароля** (`auth`). 

!!! Сейчас нельзя запросить письмо со ссылкой на смену пароля (возможно, стоит добавить потом).

Основное действие (лайк, регистрация, смена пароля) не должно ломаться/тормозить из-за недоступности `notifications-service`, поэтому `asyncio.create_task(notify_user(...))` не `await`.
`notify_user` не бросает исключений, просто логирует `warning`.

Шаблоны для событий (`review_liked`, `review_disliked`, `user_registered`, `password_changed`) добавлены в миграциию.

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
