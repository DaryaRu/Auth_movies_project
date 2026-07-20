# Онлайн-кинотеатр

Онлайн-кинотеатр состоит из нескольких сервисов:

- **auth-service** — аутентификация, управление пользователями, ролями, правами и подписками. Выдаёт JWT токены.
- **movies-service** — API контента: фильмы, жанры, персоны. Верифицирует токены и проверяет уровень подписки.
- **movies-admin** — Django-администрирование каталога фильмов. Вход через auth-service.
- **movies-etl** — синхронизация данных из PostgreSQL в Elasticsearch.
- **analytics-service** — приём событий пользователей и публикация в Kafka. Верифицирует JWT, отдаёт `202 Accepted` без ожидания подтверждения от брокера.
- **nginx** — единая точка входа, проксирует запросы к сервисам, добавляет `X-Request-Id`.

**Стек:** FastAPI, Django, PostgreSQL, Redis, Elasticsearch, Kafka, JWT RS256, Argon2, OAuth 2.0, Docker


## Первый запуск

**1. Создать `.env` из примера и заполнить переменные:**

```bash
cp .env.example .env
```

Обязательно указать пути к RSA-ключам (внутренние пути контейнера, куда они монтируются):

```
PRIVATE_KEY_PATH=/app/keys/private.pem
PUBLIC_KEY_PATH=/app/keys/public.pem
```

Файлы ключей (`private.pem`, `public.pem`) создадутся в корне проекта на следующем шаге.

**2. Поднять сервис:**

```bash
make init
```

Команда последовательно выполнит: `keys` → `build` → `up`.
Миграции применяются автоматически при старте через отдельный контейнер.

**3. Создать суперпользователя:**

```bash
make superuser
```

Интерактивный ввод email и пароля. Суперпользователь нужен для управления ролями, правами и подписками через API, а также для входа в Django-админку.

**4. Открыть документацию API:**

```
http://localhost/api/auth/openapi    — auth-service
http://localhost/api/movies/openapi  — movies-service
http://localhost/admin/              — Django-админка
```


## Архитектура доступа к контенту

Доступ к фильмам управляется через уровень подписки:

1. В auth-сервисе создаётся подписка с числовым значением `level` (например, `free=0`, `premium=1`).
2. При регистрации пользователю автоматически назначается подписка `free`.
3. В JWT-токене передаются поля `subscription_code` и `subscription_level`.
4. В Django-админке каждому фильму выставляется `subscription_level` — минимальный уровень для просмотра.
5. ETL переносит `subscription_level` из PostgreSQL в Elasticsearch.
6. movies-service при запросе деталей фильма (`GET /api/v1/films/{id}/`) сравнивает уровень пользователя с уровнем фильма. Если уровень недостаточен — возвращает 403.

Список фильмов и поиск — публичные эндпоинты, доступны всем.


## Команды

`make init` — первый запуск: ключи → сборка → запуск

`make fresh` — полный сброс: удалить тома → пересобрать → запустить → миграции. После завершения создать суперпользователя заново: `make superuser`

`make fresh-nc` — то же что `fresh`, но без кэша Docker

`make rebuild` — пересобрать образы и перезапустить без удаления данных

`make build` — собрать Docker-образы

`make up` — запустить контейнеры в фоне

`make down` — остановить контейнеры (данные сохраняются)

`make down-v` — остановить контейнеры и удалить все тома

`make auth-migrate` — применить все миграции auth-сервиса

`make superuser` — создать суперпользователя (интерактивный ввод)

`make logs` — логи auth-сервиса

`make shell` — открыть psql-сессию в БД auth-сервиса

`make keys` — сгенерировать RSA-ключи (пропускается, если файлы уже есть)

`make revision name="..."` — применить миграции и создать новую по текущим моделям

`make revision-fresh name="..."` — создать миграцию без предварительного `upgrade head` (чистая БД)

`make test-auth` — функциональные тесты auth-сервиса

`make test-movies` — функциональные тесты movies-сервиса

`make test-all` — тесты всех сервисов

`make logs-analytics` — логи analytics-service

`make analytics-event TOKEN=eyJhbGci...` — отправить тестовое событие (токен получить через `/api/v1/login/`)


## Переиндексация Elasticsearch

При изменении маппинга индекса (например, добавлении нового поля) нужно удалить индекс — ETL пересоздаст его автоматически при следующем запуске:

```bash
docker compose exec elasticsearch curl -X DELETE "http://localhost:9200/movies"
```

При `make fresh` / `make fresh-nc` делать это не нужно — тома удаляются автоматически.


## Проверка входа через Google

### Получение GOOGLE_CLIENT_ID и GOOGLE_CLIENT_SECRET

1. Открыть [Google Cloud Console](https://console.cloud.google.com/) и создать проект (или выбрать существующий).
2. Перейти в **APIs & Services → OAuth consent screen**:
   - User Type: **External**
   - Заполнить название приложения и email
   - В разделе **Test users** добавить Google-аккаунты, которые будут использоваться для тестирования
3. Перейти в **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**:
   - Application type: **Web application**
   - В **Authorized redirect URIs** добавить `http://localhost/api/v1/auth/google/callback/`
4. Скопировать **Client ID** и **Client Secret** (`GOOGLE_CLIENT_ID` и `GOOGLE_CLIENT_SECRET`).

### Запуск

Предварительно:
1. В `.env` заполнены `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `OAUTH_REDIRECT_BASE_URL=http://localhost`.
2. Сервис запущен.

Шаги проверки:
1. В Swagger (`http://localhost/api/auth/openapi`) выполнить `GET /api/v1/auth/google/` — сервис вернёт `{"url": "https://accounts.google.com/..."}`.
2. Скопировать `url` из ответа и открыть в браузере.
3. Выбрать тестовый аккаунт.
4. Google сделает редирект на `http://localhost/api/v1/auth/google/callback/?code=...&state=...`.
5. Сервис вернёт JSON с `access_token`.
6. Проверить что пользователь создался в БД: `make shell` → `SELECT * FROM users;` и `SELECT * FROM oauth_accounts;`.

## Проверка входа через VK ID

### Получение VK_CLIENT_ID и VK_CLIENT_SECRET

1. Открыть [VK ID для разработчиков](https://id.vk.com/about/business/go/accounts) и создать приложение (или выбрать существующее).
2. Перейти в **Настройки приложения**:
   - Скопировать **ID приложения** (`VK_CLIENT_ID`)
   - Скопировать **Защищённый ключ** (`VK_CLIENT_SECRET`)
3. В разделе **Подключение авторизации**:
   - В поле **Базовый домен** добавить `localhost`
   - В поле **Доверенный Redirect URL** добавить `http://localhost/api/v1/auth/vk/callback/`
4. Сохранить изменения.

### Запуск

Предварительно:
1. В `.env` заполнены `VK_CLIENT_ID`, `VK_CLIENT_SECRET`, `OAUTH_REDIRECT_BASE_URL=http://localhost`.
2. Сервис запущен.

Шаги проверки:
1. В Swagger (`http://localhost/api/auth/openapi`) выполнить `GET /api/v1/auth/vk/` — сервис вернёт `{"url": "https://id.vk.ru/authorize?..."}`.
2. Скопировать `url` из ответа и открыть в браузере.
3. Разрешить доступ приложению.
4. VK ID сделает редирект на `http://localhost/api/v1/auth/vk/callback/?code=...&state=...&device_id=...`.
5. Сервис вернёт JSON с `access_token`.
6. Проверить что пользователь создался в БД: `make shell` → `SELECT * FROM users;` и `SELECT * FROM oauth_accounts;`.
## Проверка входа через Yandex

### Получение YANDEX_CLIENT_ID и YANDEX_CLIENT_SECRET

1. Перейдите по ссылке https://oauth.yandex.ru/client/new/id.
2. Выберите создание приложения для авторизации пользователей.
3. Пройдите верификацию с помощью ГосУслуг.
4. Заполните поля формы (название сервиса, иконка, почта для связи).
5. Выберите, к каким данным нужен доступ вашему приложению.
6. Далее укажите ссылку для редиректа в поле RedirectURI `http://localhost/api/v1/auth/yandex/callback/`

### Запуск

Предварительно:
1. В `.env` заполнены `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET`, `OAUTH_REDIRECT_BASE_URL=http://localhost`.
2. Сервис запущен.

Шаги проверки:
1. В Swagger (`http://localhost/api/auth/openapi`) выполнить `GET /api/v1/auth/yandex/` — сервис вернёт `{"url": "https://oauth.yandex.ru/authorize?..."}`.
2. Скопировать `url` из ответа и открыть в браузере.
3. Yandex сделает редирект на `http://localhost/api/v1/auth/yandex/callback/?code=...&state=...`.
4. Сервис вернёт JSON с `access_token`.
5. Проверить что пользователь создался в БД: `make shell` → `SELECT * FROM users;` и `SELECT * FROM oauth_accounts;`.


## Работа с ролями и правами

Роли и права предназначены для управления административными действиями (модерация контента, работа с пользователями). Все операции доступны только суперпользователю. Перед запросами получить access-токен через `POST /api/v1/login/` и передавать в заголовке:

```
Authorization: Bearer <access_token>
```

Когда access-токен истечёт — обновить через `POST /api/v1/refresh/`.

### Как назначить роль пользователю

1. Создать право: `POST /api/v1/permissions/` с `{"code": "content:edit", "name": "Редактировать контент"}`
2. Создать роль: `POST /api/v1/roles/` с `{"name": "content_manager"}`
3. Добавить право к роли: `POST /api/v1/roles/{role_id}/permissions/{permission_id}/`
4. Назначить роль пользователю: `POST /api/v1/roles/{role_id}/users/{user_id}/`

После следующего логина пользователя в JWT-токене появится поле `permissions` со списком кодов прав, например `["content:edit"]`.

### Использование прав в сервисах-потребителях

Сами по себе роли доступ не ограничивают — сервис-потребитель (movies-service, movies-admin) должен самостоятельно извлечь `permissions` из JWT и проверить наличие нужного права перед выполнением операции.
Сейчас все административные операции доступны только суперпользователю. Чтобы разграничить доступ через роли, нужно добавить проверку `permissions` на соответствующих эндпоинтах.


## Работа с подписками

Подписки управляют доступом к контенту. Уровень `0` соответствует бесплатному доступу (`free`), более высокие уровни — платным тарифам.

**Создать тип подписки** (только суперпользователь):
```
POST /api/v1/subscriptions/
```

**Назначить подписку пользователю:**
```
POST /api/v1/users/{user_id}/subscription/
```

После следующего логина пользователя новый `subscription_level` отразится в JWT-токене.

**Выставить уровень фильму:** в Django-админке (`http://localhost/admin/`) открыть карточку фильма и установить поле «Уровень подписки».


## analytics-service

Сервис принимает события пользователей и публикует их в Kafka-топик `user-activity`.

**Гарантии доставки:** at-most-once на обоих уровнях. Потеря единичных событий при сбое не критична для бизнеса. At-least-once потребовало бы логики дедупликации на стороне ETL и усложнения схемы ClickHouse (ReplacingMergeTree вместо MergeTree). At-most-once даёт простую реализацию без дубликатов в хранилище.

**Реализация at-most-once:**

Клиент → analytics-service:
- Сервис принимает событие, кладёт в `asyncio.Queue` и немедленно отвечает `202 Accepted` — не дожидаясь подтверждения от Kafka
- При переполнении очереди (`KAFKA_BUFFER_SIZE=10000`) возвращает `503` и событие теряется
- При остановке сервиса события в очереди теряются

analytics-service → Kafka:
- Фоновый воркер читает очередь и публикует через `send_and_wait` с `KAFKA_ACKS=1` (подтверждение от лидера)
- При `KafkaError` событие логируется с уровнем `ERROR` и теряется — повторной отправки нет
- При недоступности Kafka воркер уходит в цикл переподключения (`KAFKA_RETRY_INTERVAL_SEC=5`) — сервис продолжает принимать запросы, очередь заполняется

ETL → ClickHouse:
- ETL коммитит offset до вставки в ClickHouse; при сбое вставки offset уже зафиксирован и событие не повторяется

**Сообщение в Kafka:** `user_id` (UUID из JWT), `event_type`, `object_id` (UUID объекта — фильм, жанр и т.п.; опционально), `payload` (произвольный JSON), `event_time` (время события на клиенте).

**Поддерживаемые типы событий:** `film_view`, `films_list_view`, `film_search`, `genre_view`, `person_view`, `person_films_view`, `search_filter_used`, `trailer_click`, `page_time_spent`, `film_progress`, `video_quality_changed`, `film_start`, `video_completed`, `player_action`.

### ETL: Kafka → ClickHouse

`analytics-etl` — читает Kafka-топик `user-activity` и переносит события в ClickHouse.

**Чтение из Kafka:**
- Подписка на топик `user-activity` в consumer group `KAFKA_GROUP_ID` (по умолчанию `analytics-etl`) с `ack_policy=ACK_FIRST` — offset коммитится до обработки сообщения (at-most-once гарантия).
- Каждое сообщение валидируется по той же union-схеме событий, что и analytics-service. Невалидные сообщения логируются и публикуются в dead-letter топик `user-activity.dlq`, не прерывая обработку остальных сообщений.
- При недоступности Kafka-брокера переподключение идёт с паузой `KAFKA_RETRY_BACKOFF_MS` (по умолчанию 1000 мс).

**Запись в ClickHouse:**
- Валидные события буферизуются в памяти и вставляются пачками — по достижении `ANALITYCS_ETL_BATCH_SIZE` (по умолчанию 1000 строк) либо по таймеру `ANALITYCS_ETL_FLUSH_INTERVAL` (по умолчанию 5 сек), смотря что наступит раньше.
- При сбое вставки — до 3 быстрых попыток с backoff (0.5с → 1с → 2с, под кратковременные сетевые сбои); если не помогло — батч логируется как потерянный и отбрасывается (что соответствует at-most-once).
- Целевая таблица — `analytics.events`: `Distributed`-таблица (шардирование `cityHash64(user_id)`, `internal_replication=true`) поверх `analytics.events_local` (`ReplicatedMergeTree`, реплицируется на 3 узла кластера `movie_cluster` для отказоустойчивости). Схема: `user_id, event_type, object_id, payload (JSON-строка), event_time, created_at`.

### Проверка

1. Поднять все контейнеры и создать суперпользователя:
   ```bash
   make fresh
   make superuser
   ```
2. Получить токен: `POST /api/v1/login/` в Swagger → `http://localhost/api/auth/openapi`
3. Отправить тестовое событие: открыть `http://localhost/api/analytics/openapi` → **Authorize** (вставить токен) → `POST /api/v1/analytics/events/` → ожидается `202`
4. Убедиться что событие попало в Kafka: `http://localhost:8080` → Topics → `user-activity` → Messages
5. Убедиться что analytics-etl перенес событие из Kafka: `make check-clickhouse`


## Трассировка

UI Jaeger доступен на `http://localhost/tracers/` — показывает трейсы всех запросов к auth-service, movies-service и movies-admin.
