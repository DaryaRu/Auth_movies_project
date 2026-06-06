init: keys build up migrate superuser

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f app

migrate:
	docker compose exec app alembic upgrade head

superuser:
	docker compose exec app python src/commands/create_superuser.py

revision:
	docker compose exec app alembic revision --autogenerate -m "$(name)"

keys:
	test -f private.pem || openssl genrsa -out private.pem 2048
	test -f public.pem || openssl rsa -in private.pem -pubout -out public.pem
