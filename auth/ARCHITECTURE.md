# Архитектура сервиса авторизации

## Назначение

Сервис отвечает за аутентификацию пользователей и управление доступом к ресурсам онлайн-кинотеатра (система управления ролями и правами доступа).

Остальные сервисы платформы онлайн-кинотеатра будут получать публичный ключ через `GET /api/v1/jwt.key/` и самостоятельно верифицировать токены без обращения к этому сервису.


## Стек

- **Веб-фреймворк** — FastAPI + Gunicorn
- **База данных** — PostgreSQL + asyncpg + SQLAlchemy async + Alembic
- **Кэш** — Redis + fastapi-cache2
- **Токены** — JWT RS256 (python-jose, асимметричные ключи)
- **Пароли** — Argon2 (argon2-cffi)
- **OAuth** — Authlib + httpx
- **CLI** — Typer (создание суперпользователя)


## Метод организации доступов

Для онлайн-кинотеатра выбрана модель **RBAC (Role-Based Access Control)** — ролевое управление доступом.


### Схема доступа

```
Пользователь → Роли → Права → Ресурсы
```

Пользователь получает набор ролей. Каждая роль содержит набор прав (`Permission`). Право — атомарное разрешение на действие в формате `область системы:действие`. Другие сервисы извлекают список прав из JWT и принимают решение об авторизации самостоятельно.

### Система прав

Право (`Permission`) идентифицируется уникальным `code` в формате `область системы:действие`. Примеры:

- `movie:watch` — смотреть фильмы
- `movie:watch_premium` — смотреть контент по подписке Premium
- `content:upload` — загружать контент
- `content:moderate` — редактировать и удалять контент
- `billing:view` — просматривать транзакции
- `admin:manage_roles` — управлять ролями и правами
- `user:view_profile` — просматривать профили пользователей

Права группируются по `category` (например, `movies`, `billing`, `content`и другие) — для группировки при отображении списка прав.


## Структура сервиса

```
src/
├── api/v1/
│   ├── auth.py
│   ├── oauth.py
│   ├── roles.py
│   ├── permissions.py
│   └── dependencies.py
├── commands/
│   └── create_superuser.py
├── core/
│   ├── app_factory.py
│   ├── cache.py
│   ├── config.py
│   ├── logger.py
│   ├── middlewares.py
│   └── routers.py
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
│   └── associations.py
├── repositories/
│   ├── base.py
│   ├── users.py
│   ├── oauth_accounts.py
│   ├── sessions.py
│   ├── roles.py
│   └── permissions.py
├── schemas/
│   ├── tokens.py
│   ├── users.py
│   ├── oauth_accounts.py
│   ├── sessions.py
│   ├── roles.py
│   └── permissions.py
├── services/
│   ├── base.py
│   ├── auth.py
│   ├── oauth.py
│   ├── oauth_providers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── google.py
│   ├── sessions.py
│   ├── roles.py
│   └── permissions.py
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
- **`services/`** — бизнес-логика. `AuthService` отвечает за регистрацию, аутентификацию, refresh-токен, логаут, смену пароля и email. `OAuthService` реализует OAuth 2.0 Authorization Code Flow. `RoleService` и `PermissionService` реализуют RBAC. `SessionService` управляет активными сессиями.
- **`services/oauth_providers/`** — реестр OAuth-провайдеров (`PROVIDERS`). Каждый провайдер — словарь с параметрами подключения и функцией `parse_user_info`. Сейчас реализован Google.
- **`repositories/`** — слой доступа к данным. Изолирует SQL-запросы от бизнес-логики. `BasePostgreSQLRepository` содержит общие операции. `SessionRepository` инкапсулирует все операции с таблицей `refresh_tokens`.
- **`models/`** — SQLAlchemy ORM-модели (`UserORM`, `OAuthAccountORM`, `RoleORM`, `PermissionORM`, M2M-таблицы).
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

Используется для двух целей:
- **Хранение сессий** — каждая сессия хранится в хэше `session:{sid}` с TTL равным сроку жизни refresh-токена. Список сессий пользователя — в множестве `user_sessions:{user_id}`.
- **Кэширование** — через `fastapi-cache2`. Сейчас кэшируется `GET /jwt.key/` (TTL 1 час).

Инициализируется в `lifespan` при старте приложения.


## Схема данных

### `users`

- `id` — уникальный идентификатор пользователя, генерируется автоматически.
- `email` — email пользователя, используется для входа. Должен быть уникальным.
- `hashed_password` — пароль в хэшированном виде (Argon2). Может быть `NULL` для пользователей, зарегистрированных через OAuth (без пароля).
- `is_superuser` — флаг суперпользователя. По умолчанию `false`.
- `is_active` — флаг активности аккаунта. По умолчанию `true`.
- `created_at`, `updated_at` — дата создания и последнего обновления записи.

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

Хранит привязку пользователя к внешнему OAuth-провайдеру. Один пользователь может иметь несколько OAuth-аккаунтов (разные провайдеры).

- `id` — уникальный идентификатор записи.
- `user_id` — ссылка на пользователя (CASCADE DELETE).
- `provider` — название провайдера (`google`, `yandex` и др.).
- `provider_user_id` — идентификатор пользователя на стороне провайдера.
- Уникальный индекс на пару `(provider, provider_user_id)`.

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

Конфигурация провайдеров — словарь `PROVIDERS` в `src/services/oauth_providers/`. Каждый провайдер задаёт `client_id`, `client_secret`, `authorize_url`, `token_url`, `userinfo_url`, `scope` и функцию `parse_user_info`.

Реализован: **Google** (`provider=google`).

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

### Доступ анонимных пользователей

Модель доступа — **закрытая по умолчанию**: все эндпоинты требуют JWT-токен, кроме явно публичных (`/registration/`, `/login/`, `/jwt.key/`).

Запрос без токена на защищённый эндпоинт → **401** `"Токен доступа не обнаружен"` (обрабатывается в `CustomHTTPBearer` до бизнес-логики).


## Тесты

Функциональные тесты поднимают реальное окружение (PostgreSQL, Redis, FastAPI) через Docker Compose и проверяют API через HTTP-клиент.


## Аутентификация и токены

- **Access-токен** — короткоживущий JWT RS256, передаётся в заголовке `Authorization: Bearer <token>`. Содержит `sub` (user_id), `is_superuser`, `sid` (ID сессии), `permissions` (список кодов прав).
- **Refresh-токен** — долгоживущий, хранится в httpOnly `secure` cookie `refresh_token`. Сессия хранится в Redis: хэш токена, IP, User-Agent, TTL = сроку жизни refresh-токена.
- **Token Rotation** — при рефреше хэш токена в Redis обновляется, выдаётся новая пара.
- **Логаут** — сессия удаляется из Redis, cookie очищается.
- **Logout-all** — все сессии пользователя удаляются из Redis, cookie очищается.
- **Смена пароля** — все активные сессии пользователя удаляются из Redis.
- **Публичный ключ** — другие сервисы платформы получают его через `GET /api/v1/jwt.key/` и верифицируют токены самостоятельно.
