# Первый запуск: генерирует ключи, собирает образы, поднимает контейнеры
init: keys build up

# Полный сброс и повторный запуск: удаляет тома, пересобирает, поднимает, мигрирует, создаёт суперпользователя
fresh: down-v build up migrate superuser

# Останавливает контейнеры и удаляет все тома (данные БД будут потеряны)
down-v:
	docker compose down -v

# Генерирует новую миграцию без предварительного upgrade head (использовать на чистой БД)
# Пример: make revision-fresh name="add_users_table"
revision-fresh:
	docker compose run --rm migrate alembic revision --autogenerate -m "$(name)"

# Пересобирает образы и перезапускает контейнеры без удаления томов
rebuild: down build up

# Собирает Docker-образы
build:
	docker compose build

# Запускает контейнеры в фоне; --remove-orphans удаляет контейнеры сервисов, которых больше нет в docker-compose.yml
up:
	docker compose up -d --remove-orphans

# Останавливает контейнеры без удаления томов
down:
	docker compose down

# Показывает логи контейнера приложения
logs:
	docker compose logs -f app

# Применяет все миграции (alembic upgrade head)
migrate:
	docker compose run --rm migrate alembic upgrade head

# Создаёт суперпользователя (интерактивный ввод email и пароля)
superuser:
	docker compose exec app python src/cli.py superuser create

# Применяет миграции и генерирует новую по текущему состоянию моделей
# Пример: make revision name="add_users_table"
revision:
	docker compose run --rm migrate alembic upgrade head
	docker compose run --rm migrate alembic revision --autogenerate -m "$(name)"

# Генерирует RSA-ключи для подписи JWT (пропускает, если файлы уже существуют)
keys:
	test -f private.pem || openssl genrsa -out private.pem 2048
	test -f public.pem || openssl rsa -in private.pem -pubout -out public.pem
