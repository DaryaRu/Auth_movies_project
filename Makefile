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

# Генерирует RSA-ключи для подписи JWT (пропускает, если файлы уже существуют)
keys:
	test -f private.pem || openssl genrsa -out private.pem 2048
	test -f public.pem || openssl rsa -in private.pem -pubout -out public.pem

# Запускает функциональные тесты auth-сервиса
test-auth:
	docker compose -f auth/tests/functional/docker-compose.yml up --build --abort-on-container-exit --exit-code-from tests; \
	docker compose -f auth/tests/functional/docker-compose.yml down -v

# Запускает функциональные тесты movies-сервиса
test-movies:
	docker compose -f movies/tests/functional/docker-compose.yml --env-file movies/tests/functional/.env \
		up --build --abort-on-container-exit --exit-code-from tests; \
	docker compose -f movies/tests/functional/docker-compose.yml --env-file movies/tests/functional/.env \
		down -v

# Запускает тесты всех сервисов
test-all: test-auth test-movies
