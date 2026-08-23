# Версия Python для функциональных тестов по умолчанию 3.12,
# для матрицы передать явно: make test-auth PYTHON_VERSION=3.10
PYTHON_VERSION ?= 3.12
export PYTHON_VERSION

# Первый запуск: генерирует ключи, собирает образы, поднимает контейнеры.
# Миграции применяются автоматически через сервис auth-migrate при старте.
init: keys build up

# Полный сброс: удаляет тома, пересобирает образы, поднимает контейнеры, применяет миграции.
# После завершения создать суперпользователя вручную: make superuser
fresh: down-v build up auth-migrate

# То же что fresh, но пересобирает образы без кэша Docker.
# Использовать когда: изменился requirements.txt, Dockerfile или кэш мешает подхватить обновления.
fresh-nc: down-v build-nc up auth-migrate

# Останавливает контейнеры и удаляет все тома (данные БД будут потеряны)
down-v:
	docker compose down -v

# Генерирует новую миграцию без предварительного upgrade head (использовать на чистой БД)
# Пример: make revision-fresh name="add_users_table"
revision-fresh:
	docker compose run --rm auth-migrate alembic revision --autogenerate -m "$(name)"

# Пересобирает образы и перезапускает контейнеры без удаления томов
rebuild: down build up

# Собирает Docker-образы
build:
	docker compose build

# Собирает Docker-образы без кэша
build-nc:
	docker compose build --no-cache

# Запускает контейнеры в фоне; --remove-orphans удаляет контейнеры сервисов, которых больше нет в docker-compose.yml
up:
	docker compose up -d --remove-orphans

# То же, что up, но дополнительно поднимает сервисы c profile analytics
# (Kafka, ClickHouse, analytics-service, analytics-etl),
# которые нужны только для работы с аналитикой.
# По дефолту они не поднимаются, так как потребуется много памяти на все.
up-analytics:
	docker compose --profile analytics up -d --remove-orphans

# Останавливает контейнеры без удаления томов
down:
	docker compose down

# Показывает логи контейнера приложения
logs:
	docker compose logs -f auth-service

# Применяет все миграции (alembic upgrade head)
auth-migrate:
	docker compose run --rm auth-migrate alembic upgrade head

# Создаёт суперпользователя (интерактивный ввод email и пароля)
superuser:
	docker compose exec auth-service python src/cli.py superuser create

# Применяет миграции и генерирует новую по текущему состоянию моделей
# (после добавления новой модели сначала пересобери образ: make rebuild)
# Пример: make revision name="add_users_table"
revision:
	docker compose run --rm auth-migrate alembic upgrade head
	docker compose run --rm auth-migrate alembic revision --autogenerate -m "$(name)"

# Открывает psql-сессию в БД auth-сервиса
shell:
	docker compose exec auth-db psql -U movies -d movies

# Генерирует RSA-ключи для подписи JWT (пропускает, если файлы уже существуют)
keys:
	test -f private.pem || openssl genrsa -out private.pem 2048
	test -f public.pem || openssl rsa -in private.pem -pubout -out public.pem

# Запускает функциональные тесты auth-сервиса
# code=$$? сохраняет реальный exit-код тестов.
test-auth:
	docker compose -f auth/tests/functional/docker-compose.yml up --build --abort-on-container-exit --exit-code-from tests; code=$$?; \
	docker compose -f auth/tests/functional/docker-compose.yml down -v; \
	exit $$code

# Запускает функциональные тесты movies-сервиса
test-movies:
	docker compose -f movies/tests/functional/docker-compose.yml --env-file movies/tests/functional/.env \
		up --build --abort-on-container-exit --exit-code-from tests; code=$$?; \
	docker compose -f movies/tests/functional/docker-compose.yml --env-file movies/tests/functional/.env \
		down -v; \
	exit $$code

# Запускает функциональные тесты analytics-сервиса
test-analytics:
	docker compose -f analytics/tests/functional/docker-compose.yml --env-file analytics/tests/functional/.env \
		up --build --abort-on-container-exit --exit-code-from tests; code=$$?; \
	docker compose -f analytics/tests/functional/docker-compose.yml --env-file analytics/tests/functional/.env \
		down -v; \
	exit $$code

# Запускает функциональные тесты user-actions-сервиса
test-user-actions:
	docker compose -f user_actions/tests/functional/docker-compose.yml --env-file user_actions/tests/functional/.env \
		up --build --abort-on-container-exit --exit-code-from tests; code=$$?; \
	sleep 2; \
	docker compose -f user_actions/tests/functional/docker-compose.yml --env-file user_actions/tests/functional/.env \
		down -v; \
	exit $$code

# Запускает функциональные тесты short-links-сервиса
test-short-links:
	docker compose -f short_links/tests/functional/docker-compose.yml --env-file short_links/tests/functional/.env \
		up --build --abort-on-container-exit --exit-code-from tests; code=$$?; \
	docker compose -f short_links/tests/functional/docker-compose.yml --env-file short_links/tests/functional/.env \
		down -v; \
	exit $$code

# Запускает функциональные тесты notifications-сервиса
test-notifications:
	docker compose -f notifications/tests/functional/docker-compose.yml --env-file notifications/tests/functional/.env \
		up --build --abort-on-container-exit --exit-code-from tests; code=$$?; \
	docker compose -f notifications/tests/functional/docker-compose.yml --env-file notifications/tests/functional/.env \
		down -v; \
	exit $$code

# Запускает тесты всех сервисов
test-all: test-auth test-movies test-analytics test-user-actions test-short-links test-notifications

# Прогоняет mypy локально по той же матрице, что и CI (build_mypy_matrix.py) —
# без Docker и без ожидания GitHub Actions. Окружения кэшируются в
# .mypy-check-venvs/, повторные запуски быстрее первого.
mypy:
	python3 .github/scripts/run_mypy_matrix.py

# Отправляет тестовое исключение в Sentry.
# Требует SENTRY_DSN в .env и запущенный стек (make up).
# Результат смотреть в Sentry -> Issues.
test-sentry-error:
	docker compose exec auth-service python3 -c "import sentry_sdk; from src.core.config import settings; sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT, traces_sample_rate=0); exec('try:\n 1/0\nexcept ZeroDivisionError as exc:\n print(\"auth-service:\", sentry_sdk.capture_exception(exc))'); sentry_sdk.get_client().flush(timeout=5)"
	docker compose exec movies-service python3 -c "import sentry_sdk; from core import config; sentry_sdk.init(dsn=config.SENTRY_DSN, environment=config.ENVIRONMENT, traces_sample_rate=0); exec('try:\n 1/0\nexcept ZeroDivisionError as exc:\n print(\"movies-service:\", sentry_sdk.capture_exception(exc))'); sentry_sdk.get_client().flush(timeout=5)"
	docker compose exec movies-admin python3 -c "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); django.setup(); import sentry_sdk; exec('try:\n 1/0\nexcept ZeroDivisionError as exc:\n print(\"movies-admin:\", sentry_sdk.capture_exception(exc))'); sentry_sdk.get_client().flush(timeout=5)"
	docker compose exec user-actions-service python3 -c "import sentry_sdk; from src.core.config import settings; sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT, traces_sample_rate=0); exec('try:\n 1/0\nexcept ZeroDivisionError as exc:\n print(\"user-actions-service:\", sentry_sdk.capture_exception(exc))'); sentry_sdk.get_client().flush(timeout=5)"

# analytics-service
logs-analytics:
	docker compose logs -f analytics-service

# Показывает логи analytics-etl, отфильтрованные по потреблению памяти (проверка FR-10/NFR-12)
logs-etl:
	docker compose logs -f analytics-etl | grep "Memory usage"

# Показывает последние 5 событий в ClickHouse (проверка цепочки analytics-service → Kafka → analytics-etl → ClickHouse)
check-clickhouse:
	docker compose exec clickhouse-1 clickhouse-client --query "SELECT * FROM analytics.events ORDER BY event_time DESC LIMIT 5"

# user-actions-service
logs-user-actions:
	docker compose logs -f user-actions-service

# notifications-service
# Шаг 1: поднимает все, что нужно для проверки полного пути от события до отправки
# письма (Kafka, БД, API, воркер, auth-service, Mailpit).
notifications-up:
	docker compose --profile analytics up -d --build \
		zookeeper kafka-0 kafka-1 kafka-2 kafka-topic-init-notifications kafka-topic-init-notification-pending kafka-topic-init-notification-ready-bulk kafka-topic-init-notification-dlq \
		notifications-db notifications-service notifications-worker notifications-scheduler mailpit auth-service user-actions-service nginx

# Шаг 2: находит template_id реального шаблона review_liked и отправляет
# тестовый POST /api/v1/notifications/ изнутри контейнера сервиса.
notifications-test-request:
	@TEMPLATE_ID=$$(docker compose exec -T notifications-db psql -U postgres -d notifications -tAc "SELECT template_id FROM templates WHERE code = 'review_liked';"); \
	if [ -z "$$TEMPLATE_ID" ]; then echo "Шаблон review_liked не найден — проверьте, что миграции применились (notifications-service healthy)"; exit 1; fi; \
	echo "template_id=$$TEMPLATE_ID"; \
	docker compose exec -T notifications-service python3 -c "import json, urllib.request; req = urllib.request.Request('http://localhost:8000/api/v1/notifications/', data=json.dumps({'user_id': '11111111-1111-1111-1111-111111111111', 'template_id': '$$TEMPLATE_ID', 'payload': {}}).encode(), headers={'Content-Type': 'application/json'}, method='POST'); resp = urllib.request.urlopen(req); print(resp.status, resp.read().decode())"

# Шаг 3: слушает notification-ready и печатает сообщения (Ctrl+C для остановки)
notifications-verify-topic:
	docker compose exec notifications-service python3 scripts/verify_ready_topic.py

# Сообщения, которые воркер не смог доставить получателю.
notifications-verify-dlq:
	docker compose exec notifications-service python3 scripts/verify_dlq_topic.py

# Полный путь от реального события до письма
# (auth-service -> notify_user -> notifications-service -> Kafka -> notifications-worker -> Mailpit),
# проверяет реальную отправку.
notifications-register-test-user:
	@EMAIL="worker-test-$$(date +%s)@example.com"; \
	echo "email=$$EMAIL"; \
	curl -s -X POST http://localhost/api/v1/registration/ \
		-H "Content-Type: application/json" \
		-d "{\"email\": \"$$EMAIL\", \"password\": \"TestPass123!\"}"; \
	echo; \
	echo "Проверить письмо: http://localhost:8025 (Mailpit), статус: make notifications-check-status"

# Последние 5 строк notifications
notifications-check-status:
	docker compose exec notifications-db psql -U postgres -d notifications -c "SELECT notification_id, notification_type, status, delivery_address, sent_at, error_message FROM notifications ORDER BY created_at DESC LIMIT 5;"

notifications-worker-logs:
	docker compose logs -f notifications-worker

notifications-scheduler-logs:
	docker compose logs -f notifications-scheduler

# Шаг 4: опускает стек, поднятый notifications-up
notifications-down:
	docker compose --profile analytics down -v
