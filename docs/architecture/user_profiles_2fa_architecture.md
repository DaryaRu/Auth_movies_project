# Двухфакторная аутентификация по телефону (auth-service)

Двухфакторная аутентификация включается, если у пользователя в профиле указан `phone` (тогда вход требует второго шага), если телефона нет, то пользователь логинится в одно действие.

## Компоненты

- `AuthService` оркестрирует логин целиком.
- `TwoFactorService` отвечает за генерацию, хранение и проверку кода, rate limiting отправки и проверки. `TwoFactorService` работает с абстракцией, конкретный провайдер подменяем.
- `SMSProviderBase` и `SMSCProvider` (`src/integrations/sms/`) — интерфейс отправки СМС и его реализация через SMSC.ru.
- Redis — хранилище состояния для кода и всех лимитов.

## Redis-ключи

Ключи заводит и удаляет `TwoFactorService`.

- `2fa_code:{user_id}` — код (6 цифр). TTL — `CODE_2FA_EXPIRE_SECONDS` (300 секунд).
- `2fa_attempts:{user_id}` — счетчик неверных попыток проверки текущего кода (лимит `TWO_FA_MAX_ATTEMPTS`). TTL — тот же, что и у кода.
- `2fa_send_cooldown:{phone}` — флаг «код только что отправлен». TTL — `TWO_FA_SEND_COOLDOWN_SECONDS` (60 секунд).
- `2fa_send_rate:{phone}` — счетчик отправок за текущее окно. TTL — `TWO_FA_SEND_RATE_WINDOW_SECONDS` (3600 секунд).

Код и счетчик попыток хранятся по ключу `user_id`. Кулдаун и лимит отправок за фиксированный интервал хранятся по ключу `phone`, а не `user_id`, так как защищают конкретный номер от заваливания СМС.

## Сценарий входа

1. `POST /login/` (`src/api/v1/auth.py`) принимает email/телефон + пароль (`UserRequestScheme`), вызывает `AuthService.authenticate_user()`.
2. Пользователь ищется по email/телефону, проверяется `is_active`, наличие `hashed_password` (OAuth-пользователи без пароля получают `PasswordNotSetException`) и сам пароль.
3. Если пароль верный и `user.phone` не пуст, `TwoFactorService.send_code(user.id, user.phone)` генерирует код, кладет его в Redis и отправляет через `SMSProviderBase`, после чего `authenticate_user()` бросает `TwoFactorRequiredException`.
4. Роутер ловит это исключение и возвращает `200 {"two_fa_required": true}` (`TwoFactorRequiredScheme`) без `access_token` и без `refresh_token`-cookie. Если телефона нет, то шаги 3-4 пропускаются, и `/login/` сразу отдает токены тем же путем, что и обычный логин.
5. Клиент вызывает `POST /login/verify-phone/` с email/телефоном и кодом (`VerifyTwoFactorRequestScheme`).
6. `AuthService.verify_two_factor_login()` заново ищет пользователя по email/телефону и вызывает `TwoFactorService.verify_code()`.
7. При успехе тот же путь выдачи токенов, что у обычного логина и у OAuth (`_create_user_session` — общая точка входа для всех способов аутентификации, различается только значением `auth_method`).

Код сначала сохраняется в Redis, и только потом уходит СМС-провайдеру. Так как если бы СМС реально ушла, а последующая запись в Redis не прошла (кратковременный сбой), пользователь получил бы на телефон настоящий код, который в принципе никогда не подтвердится, потому что его нет в хранилище.

## Rate limiting

- **Кулдаун на отправку** (`2fa_send_cooldown:{phone}`, 60 секунд) — нельзя запросить код чаще раза в минуту на один номер. Первая линия защиты от быстрого спама СМС.
- **Лимит отправок за фиксированный интервал** (`2fa_send_rate:{phone}`, 5 за интервал) — вторая линия: даже если кто-то выдерживает кулдаун и дергает `/login/` раз в минуту, за интервал больше 5 СМС на номер не уйдет.
- **Лимит попыток проверки** (`2fa_attempts:{user_id}`, 5 попыток на код) — при неверном коде счетчик растет, код остается в Redis (можно повторить попытку), при превышении — `TooManyAttemptsException` до следующего `send_code()` (он сбрасывает счетчик).

У всех трех в качестве ключа не IP+User-Agent, а `phone`/`user_id`, чтобы атакующий не мог обойти лимит, меняя IP или User-Agent между запросами.

## СМС-провайдер

`SMSCProvider` (`src/integrations/sms/smsc_provider.py`) — HTTP-вызов `smsc.ru/sys/send.php` с `SMSC_LOGIN`/`SMSC_PASSWORD`. При `SMSC_TEST_MODE=True` (значение по умолчанию) добавляется параметр `test=1` — сообщение проходит через тот же реальный API и получает статус «Доставлено», но реально не отправляется и не тарифицируется. Для боевой отправки достаточно `SMSC_TEST_MODE=False`, код интеграции не меняется.

Таймаут запроса — 10 секунд. Без него `aiohttp` использует дефолт в 5 минут, и есть риск проиграть гонку 60-секундному `proxy_read_timeout` nginx. При сетевой ошибке или таймауте — до 3 попыток с экспоненциальным backoff и джиттером через декоратор `@async_backoff` (`src/utils/backoff.py`) на `_request()`. Ответы самого SMSC с `error_code` (например, «message denied») не ретраятся.

## Смена номера телефона

Смена номера (`POST /change-phone-request/` и `POST /confirm-phone/`) устроена по тому же паттерну, что вход по СМС, но у него отдельный `PhoneChangeService`, свои Redis-ключи, свои настройки в конфиге. Общее — только `SMSProviderBase`/`SMSCProvider` (интерфейс отправки) и `SendCooldownException`.

### Redis-ключи

- `phone_change:{user_id}` — хеш с полями `new_phone` + `sms_code`. TTL — `PHONE_CHANGE_CODE_EXPIRE_SECONDS` (300 секунд).
- `phone_change_attempts:{user_id}` — счетчик неверных попыток проверки текущего кода (лимит `PHONE_CHANGE_MAX_ATTEMPTS`). TTL — тот же, что и у кода.
- `phone_change_send_cooldown:{new_phone}` — флаг «код только что отправлен». TTL — `PHONE_CHANGE_SEND_COOLDOWN_SECONDS` (60 секунд).
- `phone_change_send_rate:{new_phone}` — счетчик отправок за текущее окно. TTL — `PHONE_CHANGE_SEND_RATE_WINDOW_SECONDS` (3600 секунд).

Код хранится хешем, а не строкой, так как вместе с кодом нужно хранить и сам `new_phone`.

### Сценарий смены

1. `POST /change-phone-request/` (авторизация обязательна) — `PhoneChangeRequestScheme` (`new_phone` + текущий `password`). `AuthService.request_phone_change()` проверяет пароль (`VerifyPasswordException`) и уникальность `new_phone` среди других аккаунтов, затем в `PhoneChangeService.request_change()`. Номер в БД пока не меняется.
2. `PhoneChangeService.request_change()` — тот же порядок Redis → СМС, что у `TwoFactorService.send_code()`: код и `new_phone` пишутся в Redis-хеш до вызова провайдера. Кулдаун и лимит отправок за фиксированный интервал фиксируются только после успешной отправки, чтобы неудачная отправка не съедала попытку пользователя.
3. `POST /confirm-phone/` — `PhoneChangeConfirmScheme` (только `code`). `PhoneChangeService.confirm_change()` сначала проверяет лимит попыток (`PHONE_CHANGE_MAX_ATTEMPTS`), затем сверяет код через `secrets.compare_digest()`. При несовпадении увеличивает счетчик попыток и возвращает `None` — код остается в Redis, можно повторить. При совпадении удаляет хеш и счетчик, возвращает `new_phone`. `AuthService.confirm_phone_change()` превращает `None` в `InvalidPhoneChangeCodeException`, а отсутствие записи в Redis — в `NoPendingPhoneChangeException`.
4. При успешном подтверждении номер обновляется в БД, вызывается `delete_all_sessions()` для отзыва всех сессий пользователя.

### Отличия от 2FA-логина

- Требует пароль на первом шаге запроса, а у 2FA-логина пароль уже проверен раньше, на шаге `authenticate_user()`, до входа в блок кода из СМС.
- В Redis вместе с кодом хранятся еще и данные самого запроса (`new_phone`) — у 2FA-логина в Redis только код, потому что номер телефона уже есть в БД.

## Ручная проверка сценария: логин с 2FA и смена номера

1. `POST /login/` с `email`+`password` пользователя, у которого уже есть `phone` → `200 {"two_fa_required": true}`.
2. Код лежит в Redis, реальная SMS не доставляется при `SMSC_TEST_MODE=1`: `make show-2fa-code-by-email email=...` — сам найдет `user_id` через psql и прочитает `2fa_code:{user_id}`.
3. `POST /login/verify-phone/` с тем же `email` и кодом → выдача токена, `refresh_token` в cookie.
4. `POST /change-phone-request/` с `new_phone`+`password`, заголовок `Authorization: Bearer <access_token>` из шага 3 → `204`. SMSC даже в виртуальном режиме может отклонять произвольные несуществующие номера (`error_code=6`) (скорее всего происходит реальная проверка у оператора, а не формальная проверка формата). Сейчас в тестах и примерах схем используются `+79621234567`, `+79621234568`, заменить, если перестанет работать.
5. `make show-phone-change-code-by-email email=...` — код лежит в Redis-хеше `phone_change:{user_id}`, поле `sms_code`.
6. `POST /confirm-phone/` с кодом, тем же токеном → `200`, `phone` обновлен. `ACCESS_TOKEN_EXPIRE_MINUTES=5` и `PHONE_CHANGE_CODE_EXPIRE_SECONDS=300` совпадают по времени; если между шагом 3 и этим шагом прошло больше 5 минут, токен из шага 3 уже просрочен и `/confirm-phone/` ответит `401 {"error": "Ошибка декодирования токена"}`. Нужно перелогиниться.
7. После успешного подтверждения сессия отзывается немедленно `delete_all_sessions()`. Следующий запрос с этим токеном получит `401 {"error": "Невалидный токен"}` (`TokenExeption`). Нужен новый `/login/`.
8. Повторный `POST /login/` тем же `email` → снова `two_fa_required: true`, потому что аккаунт с этим email теперь просто имеет другой (новый) `phone` — 2FA включается по факту наличия телефона, а не по конкретному номеру. Логин старым номером в поле `phone` (а не email) даст `404 UserNotFoundException` — старый номер уже ничей.

## Ограничения текущего решения

- **2FA не проверяется при входе через OAuth.** `authenticate_oauth_user()` создает сессию напрямую, минуя `authenticate_user()` и весь описанный выше флоу, даже если у пользователя указан телефон. Открытый вопрос, решение не принято — см. `user_profiles_architecture.md`, раздел «Ограничения текущего решения».
- **Только один канал подтверждения (СМС).** Сервис и Redis-ключи спроектированы под конкретный канал (`2fa_code`, не `2fa_code_sms`/`2fa_code_email`). `SMSProviderBase` как абстракция это не блокирует, при добавлении второго канала потребуется только доработка `TwoFactorService`.
