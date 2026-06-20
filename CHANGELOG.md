# Changelog

### Добавлено

- `src/models/oauth_accounts.py` — модель `OAuthAccountORM` (привязка пользователя к внешнему провайдеру (`provider`, `provider_user_id`)). Уникальный индекс на пару `(provider, provider_user_id)`.
- `src/models/users.py` — обратная связь `oauth_accounts` в `UserORM`. Поле `hashed_password` сделано nullable для поддержки OAuth-пользователей без пароля.
- `src/schemas/oauth_accounts.py` — схемы `OAuthAccountResponseScheme` и `OAuthRedirectURLScheme`.
- `src/repositories/oauth_accounts.py` — репозиторий `OAuthAccountsPostgreSQLRepository` с методами `get_by_provider_data` и `create_oauth_account`.
- `src/utils/db_manager.py` — репозиторий `oauth_accounts` добавлен в `DBManager`.
- `src/exceptions.py` — исключения `OAuthProviderNotFoundException`, `OAuthEmailNotFoundException`, `PasswordAlreadySetException` и соответствующие HTTP-исключения.
- `requirements.txt` — зависимости `authlib==1.7.2` и `httpx==0.28.1`.
- Миграция `add_oauth_accounts_table`: создаётся таблица `oauth_accounts`, делает `hashed_password` nullable.

#### Сервис

- `src/services/oauth.py` — сервис `OAuthService`: формирует URL авторизации, обменивает code на данные пользователя через Authlib, находит или создаёт пользователя, выдаёт JWT-токены.
- `src/services/oauth_providers/` — пакет с реестром провайдеров: `base.py` (`OAuthUserInfo`), `google.py` (`google_provider`), `__init__.py` (реестр `PROVIDERS`).
- `src/services/oauth_providers/__init__.py` — Google провайдер регистрируется только если `GOOGLE_CLIENT_ID` и `GOOGLE_CLIENT_SECRET` заполнены. Без них сервис запускается, `/auth/google/` возвращает 400.
- `src/services/auth.py` — метод `set_password`: проверяет что `hashed_password is None`, хэширует и сохраняет пароль.

#### API

- `src/api/v1/oauth.py` — два эндпоинта:
  - `GET /api/v1/auth/{provider}/` — генерирует `state`, сохраняет его в httpOnly cookie `oauth_state` (TTL 5 минут), возвращает URL авторизации провайдера в теле ответа.
  - `GET /api/v1/auth/{provider}/callback/` — проверяет `state` из URL, вызывает `OAuthService.authenticate`, удаляет cookie `oauth_state`, устанавливает `refresh_token` в httpOnly cookie, возвращает `access_token` в теле ответа.
- `src/api/v1/dependencies.py` — зависимости `get_oauth_service` и `OAuthServiceDep`.
- `src/api/v1/auth.py` — эндпоинт `POST /api/v1/set-password/`: установка пароля для OAuth-пользователя с `hashed_password=None`. Если пароль уже установлен 409.
- `src/schemas/users.py` — схема `SetPasswordRequestScheme` с полем `password`.
- `src/core/config.py` — настройки `OAUTH_REDIRECT_BASE_URL`, `OAUTH_STATE_EXPIRE_SECONDS`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.
- `src/core/routers.py` — зарегистрирован `oauth_router`.
