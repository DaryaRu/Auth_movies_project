# Архитектура сервиса авторизации

## Назначение

Сервис отвечает за аутентификацию пользователей и управление доступом к ресурсам онлайн-кинотеатра. Реализована гибридная модель доступа:

- **RBAC** (Role-Based Access Control) — роли и права для административных действий (управление контентом, пользователями, модерация).
- **Подписки** — числовой уровень доступа к контенту (`subscription_level`). Определяет, какие фильмы пользователь может смотреть.

Остальные сервисы платформы получают публичный ключ через `GET /api/v1/jwt.key/` и самостоятельно верифицируют токены без обращения к этому сервису. Оба механизма доступа передаются в JWT и проверяются на стороне потребителя.


## Стек

- **Веб-фреймворк** — FastAPI + Gunicorn
- **База данных** — PostgreSQL + asyncpg + SQLAlchemy async + Alembic
- **Кэш** — Redis + fastapi-cache2
- **Токены** — JWT RS256 (python-jose, асимметричные ключи)
- **Пароли** — Argon2 (argon2-cffi)
- **OAuth** — Authlib + httpx
- **CLI** — Typer (создание суперпользователя)


## Модель доступа

### RBAC — административные действия

```
Пользователь → Роли → Права → Административные действия
```

Роли и права предназначены для управления административными действиями: модерация контента, управление пользователями, работа с каталогом фильмов. Не используются для ограничения доступа к просмотру фильмов.

Пользователь получает набор ролей. Каждая роль содержит набор прав (`Permission`). Права из JWT извлекаются сервисами-потребителями и используются для принятия решения об авторизации самостоятельно.

**Пример роли и прав:**

Роль `content_manager` может включать права:
- `content:edit` — редактировать карточки фильмов
- `content:delete` — удалять контент
- `subscriptions:write` — создавать и обновлять типы подписок

Право (`Permission`) идентифицируется уникальным `code` в формате `область:действие` (строчные буквы, цифры, подчёркивания). Права группируются по `category` (например, `content`, `subscriptions`) — для группировки при отображении.

### Подписки — доступ к контенту

```
Пользователь → Подписка (level) → Фильм (subscription_level) → Доступ
```

Каждому пользователю назначается подписка с числовым `level`. При регистрации автоматически назначается подписка `free` (level=0).

**Пример уровней подписок:**

- `free` (level=0) — фильмы с `subscription_level = 0`, доступны всем без авторизации
- `base` (level=1) — фильмы с `subscription_level ≤ 1`
- `premium` (level=2) — фильмы с `subscription_level ≤ 2`

Каждому фильму в Django-админке выставляется минимальный уровень для просмотра (`subscription_level`). Проверка выполняется в movies-service в `movies/src/api/v1/films.py`, эндпоинт `film_details`: уровень пользователя из JWT сравнивается с уровнем фильма (`user.subscription_level >= film.subscription_level`). Если условие не выполнено — возвращает 403. Фильмы с `subscription_level = 0` доступны всем без авторизации.

`level` уникален — нельзя создать две подписки с одинаковым числовым значением.

Суперпользователь обходит проверку подписки и имеет доступ ко всему контенту.


## Структура сервиса

```
src/
├── api/v1/
│   ├── auth.py
│   ├── oauth.py
│   ├── roles.py
│   ├── permissions.py
│   ├── subscriptions.py
│   ├── user_subscriptions.py
│   └── dependencies.py
├── commands/
│   └── create_superuser.py
├── core/
│   ├── app_factory.py
│   ├── cache.py
│   ├── config.py
│   ├── limiter.py
│   ├── logger.py
│   ├── middlewares.py
│   ├── routers.py
│   └── tracers.py
├── databases/
│   ├── pg.py
│   └── redis.py
├── migrations/
│   └── versions/
├── models/
│   ├── users.py
│   ├── oauth_accounts.py
│   ├── roles.py
│   ├── permissions.py
│   ├── subscriptions.py
│   ├── user_subscriptions.py
│   └── associations.py
├── repositories/
│   ├── base.py
│   ├── users.py
│   ├── oauth_accounts.py
│   ├── sessions.py
│   ├── roles.py
│   ├── permissions.py
│   ├── subscriptions.py
│   └── user_subscriptions.py
├── schemas/
│   ├── tokens.py
│   ├── users.py
│   ├── oauth_accounts.py
│   ├── sessions.py
│   ├── roles.py
│   ├── permissions.py
│   ├── subscriptions.py
│   └── user_subscriptions.py
├── services/
│   ├── base.py
│   ├── auth.py
│   ├── oauth.py
│   ├── sessions.py
│   ├── roles.py
│   ├── permissions.py
│   ├── subscriptions.py
│   └── user_subscriptions.py
├── integrations/
│   └── oauth/
│       ├── base_provider.py
│       ├── providers_factory.py
│       ├── google_provider.py
│       ├── yandex_provider.py
│       └── vk_provider.py
├── utils/
│   ├── db_manager.py
│   ├── hashes.py
│   ├── security.py
│   └── tokens.py
├── exceptions.py
├── cli.py
└── main.py
tests/functional/
├── fixtures/
│   ├── users.py
│   ├── roles.py
│   └── permissions.py
├── src/
│   ├── test_auth.py
│   ├── test_oauth.py
│   ├── test_roles.py
│   └── test_permissions.py
├── utils/
│   ├── check_methods.py
│   ├── constants.py
│   ├── helpers.py
│   ├── wait_for_pg.py
│   └── wait_for_redis.py
├── conftest.py
├── settings.py
└── pytest.ini
```

- **`main.py`** — точка входа приложения: FastAPI app, подключение middleware, роутеров, инициализация Redis в lifespan.
- **`api/v1/`** — HTTP-интерфейс: роутеры и зависимости FastAPI. Приём запросов, вызов сервисов и формирование ответов.
- **`services/`** — бизнес-логика. `AuthService` отвечает за регистрацию, аутентификацию, refresh-токен, логаут, смену пароля и email. `OAuthService` реализует OAuth 2.0 Authorization Code Flow. `RoleService` и `PermissionService` реализуют RBAC. `SessionService` управляет активными сессиями. `SubscriptionService` управляет типами подписок. `UserSubscriptionService` назначает подписки пользователям и возвращает историю.
- **`integrations/oauth/`** — OAuth-провайдеры: `GoogleOAuthProvider`, `YandexOAuthProvider`, `VkOAuthProvider`. Каждый реализует `OAuthBaseProvider` с методами `get_auth_url` и `get_user_info`. VK использует PKCE-flow. `OAuthProviderFactory` — реестр провайдеров по `AuthProvider`.
- **`repositories/`** — слой доступа к данным. Изолирует SQL-запросы от бизнес-логики. `BasePostgreSQLRepository` содержит общие операции. `SessionRepository` инкапсулирует все операции с таблицей `refresh_tokens`.
- **`models/`** — SQLAlchemy ORM-модели (`UserORM`, `OAuthAccountORM`, `RoleORM`, `PermissionORM`, `SubscriptionORM`, `UserSubscriptionORM`, M2M-таблицы).
- **`schemas/`** — Pydantic-схемы для валидации входных данных и сериализации ответов.
- **`databases/`** — подключение к PostgreSQL и Redis, предоставляет объекты для внедрения зависимостей.
- **`core/`** — конфигурация из `.env` (pydantic-settings), настройка логирования, фабрика приложения, регистрация роутеров, кэш, middleware.
- **`commands/`** — CLI-команды на Typer. Сейчас одна команда: создание суперпользователя.
- **`utils/`** — вспомогательные модули: `DBManager` (контекстный менеджер сессии), `JWTTokenService`, `HashArgon2Service`, `CustomHTTPBearer`.
- **`cli.py`** — точка входа CLI: регистрирует команды Typer.
- **`exceptions.py`** — исключения.


## Хранилища

### PostgreSQL

Основное хранилище данных. Используется через SQLAlchemy async ORM. Миграции — Alembic.

### Redis

Используется для:
- **Хранение сессий** — каждая сессия хранится в хэше `session:{sid}` с TTL равным сроку жизни refresh-токена. Список сессий пользователя — в множестве `user_sessions:{user_id}`.
- **Кэширование** — через `fastapi-cache2`. Кэшируется `GET /jwt.key/` (TTL 1 час).
- **Rate limiting** — счётчики запросов для `slowapi`.

Инициализируется в `lifespan` при старте приложения.


## Схема данных

### `users`

- `id` — уникальный идентификатор пользователя, генерируется автоматически.
- `email` — email для входа. Nullable.
- `phone` — номер телефона для входа. Nullable. Формат `+X...`.
- `hashed_password` — пароль в хэшированном виде (Argon2). Nullable — для пользователей, зарегистрированных через OAuth.
- `is_superuser` — флаг суперпользователя. По умолчанию `false`.
- `is_active` — флаг активности аккаунта. По умолчанию `true`.
- `created_at`, `updated_at` — дата создания и последнего обновления записи.

Для входа требуется хотя бы одно из двух: `email` или `phone`.

### `roles`

- `id` — уникальный идентификатор роли, генерируется автоматически.
- `name` — название роли. Должно быть уникальным.
- `description` — описание роли. Может быть пустым.
- `is_active` — флаг активности роли. По умолчанию `true`.
- `is_system` — флаг системной роли. Системные роли нельзя удалить через API (вернётся 409). По умолчанию `false`.
- `created_at`, `updated_at` — дата создания и последнего обновления записи.

### `permissions`

- `id` — уникальный идентификатор права, генерируется автоматически.
- `code` — уникальный код права в формате `область системы:действие`, например `movie:watch`. Не может быть пустым, проиндексирован.
- `name` — человекочитаемое название права. Не может быть пустым.
- `description` — описание права. Может быть пустым.
- `category` — категория для группировки прав в интерфейсе, например `movies`, `billing`. По умолчанию `"general"`.
- `created_at`, `updated_at` — дата создания и последнего обновления записи.

### `oauth_accounts`

Хранит привязку пользователя к внешнему OAuth-провайдеру. Один пользователь может иметь несколько OAuth-аккаунтов (разные провайдеры). Таблица **партиционирована по LIST(provider)** — отдельные партиции для `google`, `yandex`, `vk`.

- `id` — уникальный идентификатор записи.
- `user_id` — ссылка на пользователя (CASCADE DELETE).
- `provider` — название провайдера (`google`, `yandex`, `vk`).
- `provider_user_id` — идентификатор пользователя на стороне провайдера.
- Уникальный индекс на пару `(provider, provider_user_id)`.

### `subscriptions`

Типы подписок. `level` уникален — нельзя создать две подписки с одинаковым числовым значением.

- `id` — уникальный идентификатор.
- `code` — уникальный код, например `free`, `premium`.
- `level` — числовое значение уровня (уникальное). `0` — бесплатный доступ.
- `description` — описание подписки.
- `is_active` — активна ли подписка.

### `user_subscriptions`

Назначенные пользователям подписки.

- `id` — уникальный идентификатор.
- `user_id` — ссылка на пользователя.
- `subscription_id` — ссылка на тип подписки.
- `started_at` — дата начала.
- `expires_at` — дата окончания. Истёкшие подписки деактивируются при следующем логине.
- `is_active` — активна ли подписка.

### `user_roles`

Связывает пользователей и роли. При удалении пользователя или роли связи удаляются каскадно.

- `user_id` — ссылка на пользователя.
- `role_id` — ссылка на роль.

### `role_permissions`

Связывает роли и права. При удалении роли или права связи удаляются каскадно.

- `role_id` — ссылка на роль.
- `permission_id` — ссылка на право.


## API

### Аутентификация

Публичные эндпоинты (без токена):

- `POST /api/v1/registration/` — 201 — регистрация пользователя
- `POST /api/v1/login/` — 200 — вход, получение токенов
- `GET /api/v1/jwt.key/` — 200 — публичный ключ для верификации JWT
- `GET /health` — 200 — healthcheck

Защищённые эндпоинты (требуют JWT):

- `POST /api/v1/refresh/` — 200 — ротация токенов
- `POST /api/v1/logout/` — 204 — выход, отзыв текущего refresh-токена
- `POST /api/v1/logout-all/` — 204 — выход со всех устройств, отзыв всех активных сессий
- `GET /api/v1/active_sessions/` — 200 — список активных сессий текущего пользователя
- `PATCH /api/v1/change-email/` — 200 — смена email (требует пароль)
- `PATCH /api/v1/change-password/` — 204 — смена пароля, сброс всех сессий
- `POST /api/v1/set-password/` — 204 — установка пароля для OAuth-пользователя без пароля (409 если пароль уже установлен)
- `GET /api/v1/users/me/permissions/` — 200 — список всех прав текущего пользователя

### OAuth 2.0

Публичные эндпоинты (без токена):

- `GET /api/v1/auth/{provider}/` — 302 — редирект на страницу авторизации провайдера
- `GET /api/v1/auth/{provider}/callback/` — 200 — обработка callback, выдача JWT

#### Процесс аутентификации

```
Пользователь -> GET /auth/{provider}/ -> редирект на провайдера
Провайдер -> пользователь выбирает аккаунт
Провайдер -> GET /auth/{provider}/callback/?code=...&state=... -> JWT
```

**1.** `GET /api/v1/auth/{provider}/`

`oauth_redirect`:
- вызывает `secrets.token_urlsafe(16)` — генерирует случайный `state`.
- вызывает `OAuthService.get_redirect_url` — формирует URL авторизации провайдера.
- сохраняет `state` в httpOnly cookie `oauth_state` (TTL 5 минут).
- отвечает **302** с заголовком `Location: {authorize_url}?...`.

**2.** Браузер следует редиректу на провайдера. Пользователь видит страницу входа и выбирает аккаунт.

**3.** `GET /api/v1/auth/{provider}/callback/?code=...&state=...`

Провайдер самостоятельно делает редирект на этот URL (URI должен быть указан в консоли провайдера как разрешённый redirect URI).

**4.** Проверка state

`oauth_callback` сравнивает `state` из URL-параметра с `state` из cookie `oauth_state`. Несовпадение -> **400**.

**5.** Обмен code на токен (`OAuthService.get_user_info`)

POST на `token_url` с `code`, `client_id`, `client_secret`, `redirect_uri`. Провайдер возвращает `access_token`. Authlib сохраняет его внутри клиента.

**6.** Получение данных пользователя (`OAuthService.get_user_info`)

`client.get(userinfo_url)` — Authlib подставляет токен в заголовок автоматически. Провайдер возвращает данные пользователя. `parse_user_info` преобразует их в `OAuthUserInfo`.

**7.** Поиск или создание пользователя (`OAuthService._get_or_create_user`)

`OAuthAccountsRepository.get_by_provider_data` ищет запись в `oauth_accounts` по паре `(provider, provider_user_id)`.

**Запись найдена** — пользователь уже входил через этого провайдера. `UsersRepository.get_one_or_none_by_id` возвращает его по `user_id` из записи.

**Запись не найдена** — первый вход через этого провайдера. Если провайдер не вернул email — **400** (`OAuthEmailNotFoundException`), вернул:

- `UsersRepository.get_one_or_none_by_email` ищет пользователя по email.
  - **Email совпал** — пользователь уже зарегистрирован на сервисе (по паролю или через другого провайдера). OAuth-аккаунт привязывается к существующему пользователю. После этого он может входить и через провайдера, и прежним способом.
  - **Email не совпал** (или пользователя с таким email нет) — `UsersRepository.create_user` создаёт нового пользователя с `hashed_password=None`.
- В обоих случаях `OAuthAccountsRepository.create_oauth_account` привязывает OAuth-аккаунт к пользователю.

**8.** Выдача JWT (`OAuthService.authenticate`)

- `RolesRepository.get_user_permissions` — получает права из БД.
- `JWTTokenService.create_access_and_refresh_tokens` — создаёт пару токенов.
- `SessionService.add_session` — сохраняет сессию в Redis.
- Удаляет cookie `oauth_state`, устанавливает `refresh_token` в httpOnly cookie.
- Возвращает `access_token` в теле ответа.

#### CSRF-защита через state

`state` — случайная строка, генерируемая сервисом. Записывается в httpOnly cookie и одновременно передаётся провайдеру как параметр. При callback сервис сравнивает `state` из URL с `state` из cookie. Несовпадение → 400. Это гарантирует, что callback инициирован тем же браузером, который начал flow.

#### Поддерживаемые провайдеры

Провайдеры реализованы в `src/integrations/oauth/`. Каждый наследует `OAuthBaseProvider` и реализует `get_auth_url` и `get_user_info`.

- **Google** — стандартный Authorization Code Flow через Authlib.
- **Yandex** — обмен кода на токен через `aiohttp`, данные пользователя через Yandex Login API (JWT, HS256).
- **VK** — PKCE-flow: `code_verifier` сохраняется в Redis при старте, передаётся при обмене кода.

Также реализована отвязка OAuth-аккаунта: `DELETE /api/v1/auth/{provider}/unlink/`. Защита от отвязки последнего способа входа — если у пользователя нет пароля и только один провайдер, отвязка запрещена (409).

#### Установка пароля (`POST /api/v1/set-password/`)

OAuth-пользователь с `hashed_password=None` может установить пароль, чтобы в дальнейшем входить и по email/паролю.

Сценарий:

**1** Пользователь вошёл через Google — в БД `hashed_password=None`.
**2** Хочет добавить вход по паролю — отправляет `POST /api/v1/set-password/` с `{"password": "..."}`.
**3** Теперь может входить и через Google, и по email/паролю.

Если пароль уже установлен — **409**. Для смены существующего пароля — `PATCH /api/v1/change-password/`.


### Роли

Все эндпоинты доступны только суперпользователям (`is_superuser=True`):

- `POST /api/v1/roles/` — 201 — создать роль
- `GET /api/v1/roles/` — 200 — список всех ролей
- `GET /api/v1/roles/{role_id}/` — 200 — роль с привязанными правами
- `PATCH /api/v1/roles/{role_id}/` — 200 — частичное обновление роли
- `DELETE /api/v1/roles/{role_id}/` — 204 — удалить роль (409 если системная)
- `POST /api/v1/roles/{role_id}/users/{user_id}/` — 201 — назначить роль пользователю
- `DELETE /api/v1/roles/{role_id}/users/{user_id}/` — 204 — снять роль с пользователя
- `POST /api/v1/roles/{role_id}/permissions/{permission_id}/` — 201 — добавить право к роли
- `DELETE /api/v1/roles/{role_id}/permissions/{permission_id}/` — 204 — убрать право из роли

### Права

Все эндпоинты доступны только суперпользователям:

- `POST /api/v1/permissions/` — 201 — создать право
- `GET /api/v1/permissions/` — 200 — список всех прав
- `PATCH /api/v1/permissions/{permission_id}/` — 200 — частичное обновление права
- `DELETE /api/v1/permissions/{permission_id}/` — 204 — удалить право

### Подписки

Публичный эндпоинт (без токена):

- `GET /api/v1/subscriptions/levels/` — 200 — список доступных уровней подписок (используется movies-admin для валидации)

Только суперпользователь:

- `POST /api/v1/subscriptions/` — 201 — создать тип подписки
- `GET /api/v1/subscriptions/` — 200 — список всех подписок
- `GET /api/v1/subscriptions/{id}/` — 200 — подписка по ID
- `PATCH /api/v1/subscriptions/{id}/` — 200 — обновить подписку
- `DELETE /api/v1/subscriptions/{id}/` — 204 — удалить подписку (409 если есть активные пользователи)
- `POST /api/v1/users/{user_id}/subscription/` — 201 — назначить подписку пользователю
- `GET /api/v1/users/{user_id}/subscription/` — 200 — текущая активная подписка
- `GET /api/v1/users/{user_id}/subscription/history/` — 200 — история подписок


### Доступ анонимных пользователей

Модель доступа — **закрытая по умолчанию**: все эндпоинты требуют JWT-токен, кроме явно публичных (`/registration/`, `/login/`, `/jwt.key/`).

Запрос без токена на защищённый эндпоинт → **401** `"Токен доступа не обнаружен"` (обрабатывается в `CustomHTTPBearer` до бизнес-логики).


## Тесты

Функциональные тесты поднимают реальное окружение (PostgreSQL, Redis, FastAPI) через Docker Compose и проверяют API через HTTP-клиент.


## Аутентификация и токены

- **Access-токен** — короткоживущий JWT RS256, передаётся в заголовке `Authorization: Bearer <token>`. Содержит `sub` (user_id), `is_superuser`, `sid` (ID сессии), `permissions` (список кодов прав), `subscription_code`, `subscription_level`.
- **Refresh-токен** — долгоживущий, хранится в httpOnly `secure` cookie `refresh_token`. Сессия хранится в Redis: хэш токена, IP, User-Agent, TTL = сроку жизни refresh-токена.
- **Token Rotation** — при рефреше хэш токена в Redis обновляется, выдаётся новая пара.
- **Логаут** — сессия удаляется из Redis, cookie очищается.
- **Logout-all** — все сессии пользователя удаляются из Redis, cookie очищается.
- **Смена пароля** — все активные сессии пользователя удаляются из Redis.
- **Публичный ключ** — другие сервисы платформы получают его через `GET /api/v1/jwt.key/` и верифицируют токены самостоятельно.


## Трассировка

Интеграция OpenTelemetry с экспортом в Jaeger через OTEL Collector (gRPC, порт 4317).

- `FastAPIInstrumentor` — автоматическая трассировка HTTP-запросов.
- `SQLAlchemyInstrumentor` — трассировка SQL-запросов.
- Middleware проверяет наличие заголовка `X-Request-Id` на всех запросах кроме `/health` и `/api/auth/openapi`. Заголовок проставляется как атрибут текущего span и пробрасывается в ответ.

UI Jaeger доступен через nginx на `http://localhost/tracers/`.


## Ограничение запросов

Rate limiting реализован через `slowapi` на базе Redis. Ключ — MD5-хэш от пары IP + User-Agent (защита от смены IP при ротации).

Лимит **5 запросов в минуту** применён ко всем эндпоинтам аутентификации (`/login/`, `/registration/`, `/refresh/`, `/logout/` и др.). При превышении — **429 Too Many Requests**.
