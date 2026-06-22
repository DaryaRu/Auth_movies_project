.PHONY: test-functional test-functional-empty test-resilience test-all check-env

ENV_FILE = tests/functional/.env
DC = docker compose -f tests/functional/docker-compose.yml --env-file $(ENV_FILE)

check-env:
	@[ -f "$(ENV_FILE)" ] || { \
		echo "Error: $(ENV_FILE) not found."; \
		echo "Run: cp tests/functional/.env.example $(ENV_FILE)"; \
		exit 1; \
	}

test-functional: check-env
	$(DC) up --build --abort-on-container-exit --exit-code-from tests; \
	$(DC) down -v

test-functional-empty: check-env
	$(DC) run --rm --entrypoint pytest tests \
		/app/tests/functional/src/empty_es \
		-c /app/tests/functional/pytest.ini -v; \
	$(DC) down -v

# Runs resilience tests in-process (no real ES/Redis needed)
test-resilience: check-env
	$(DC) build fastapi; \
	$(DC) run --rm --no-deps --entrypoint sh tests \
		-c "pip install -r /app/tests/resilience/requirements.txt -q && pytest /app/tests/resilience/ -c /app/tests/resilience/pytest.ini -v"; \
	$(DC) down -v

test-all: test-functional test-functional-empty test-resilience
