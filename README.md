# Сервис авторизации

Сервис аутентификации и управления доступом для онлайн-кинотеатра. Выдаёт токены, управляет ролями и правами пользователей в соответствии с моделью RBAC. Остальные сервисы платформы получают публичный ключ через `GET /api/v1/jwt.key/` и верифицируют токены самостоятельно.

**Стек:** FastAPI, PostgreSQL, Redis, JWT RS256, Argon2, OAuth 2.0 (Authlib), Docker


## Первый запуск

**1. Создать `.env` из примера и заполнить переменные:**

```bash
cp .env.example .env
```

Обязательно указать пути к RSA-ключам (они создадутся на следующем шаге):

```
PRIVATE_KEY_PATH=keys/private.pem
PUBLIC_KEY_PATH=keys/public.pem
```

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

Интерактивный ввод email и пароля. Суперпользователь нужен для управления ролями и правами через API.

**4. Открыть документацию API:**

```
http://localhost:8000/api/openapi
```


## Команды

`make init` — первый запуск: ключи → сборка → запуск

`make fresh` — полный сброс: удалить тома → пересобрать → запустить → миграции → создать суперпользователя

`make rebuild` — пересобрать образы и перезапустить без удаления данных

`make build` — собрать Docker-образы

`make up` — запустить контейнеры в фоне

`make down` — остановить контейнеры (данные сохраняются)

`make down-v` — остановить контейнеры и удалить все тома

`make migrate` — применить все миграции

`make superuser` — создать суперпользователя (интерактивный ввод)

`make logs` — логи

`make keys` — сгенерировать RSA-ключи (пропускается, если файлы уже есть)

`make revision name="..."` — применить миграции и создать новую по текущим моделям

`make revision-fresh name="..."` — создать миграцию без предварительного `upgrade head` (чистая БД)

`make test` — запустить функциональные тесты (поднимает окружение и удаляет контейнеры после завершения)


## Проверка входа через Google

### Получение GOOGLE_CLIENT_ID и GOOGLE_CLIENT_SECRET

1. Открыть [Google Cloud Console](https://console.cloud.google.com/) и создать проект (или выбрать существующий).
2. Перейти в **APIs & Services → OAuth consent screen**:
   - User Type: **External**
   - Заполнить название приложения и email
   - В разделе **Test users** добавить Google-аккаунты, которые будут использоваться для тестирования
3. Перейти в **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**:
   - Application type: **Web application**
   - В **Authorized redirect URIs** добавить `http://localhost:8000/api/v1/auth/google/callback/`
4. Скопировать **Client ID** и **Client Secret** (`GOOGLE_CLIENT_ID` и `GOOGLE_CLIENT_SECRET`).

### Запуск

Предварительно:
1. В `.env` заполнены `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `OAUTH_REDIRECT_BASE_URL=http://localhost:8000`.
2. Сервис запущен.

Шаги проверки:
1. В Swagger (`http://localhost:8000/api/openapi`) выполнить `GET /api/v1/auth/google/` — сервис вернёт `{"url": "https://accounts.google.com/..."}`.
2. Скопировать `url` из ответа и открыть в браузере.
3. Выбрать тестовый аккаунт.
4. Google сделает редирект на `http://localhost:8000/api/v1/auth/google/callback/?code=...&state=...`.
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
1. В Swagger (`http://localhost/api/openapi`) выполнить `GET /api/v1/auth/vk/` — сервис вернёт `{"url": "https://id.vk.ru/authorize?..."}`.
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
6. Далее укажите ссылку для редиректа в поле RedirectURI `http://localhost:8000/api/v1/auth/yandex/callback/`

### Запуск

Предварительно:
1. В `.env` заполнены `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET`, `OAUTH_REDIRECT_BASE_URL=http://localhost:8000`.
2. Сервис запущен.

Шаги проверки:
1. В Swagger (`http://localhost:8000/api/openapi`) выполнить `GET /api/v1/auth/yandex/` — сервис вернёт `{"url": "https://oauth.yandex.ru/authorize?..."}`.
2. Скопировать `url` из ответа и открыть в браузере.
4. Yandex сделает редирект на `http://localhost:8000/api/v1/auth/yandex/callback/?code=...&state=...`.
5. Сервис вернёт JSON с `access_token`.
6. Проверить что пользователь создался в БД: `make shell` → `SELECT * FROM users;` и `SELECT * FROM oauth_accounts;`.


## Работа с ролями и правами

Все операции управления ролями и правами доступны только суперпользователю. Перед запросами получить access-токен через `POST /api/v1/login/` и передавать в заголовке:

```
Authorization: Bearer <access_token>
```

Когда access-токен истечёт — обновить через `POST /api/v1/refresh/`.
