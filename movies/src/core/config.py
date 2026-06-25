import os

# Название проекта. Используется в Swagger-документации
PROJECT_NAME = os.getenv("PROJECT_NAME", "movies")

# Настройки Redis
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Настройки Elasticsearch
ELASTIC_HOST = os.getenv("ELASTIC_HOST", "127.0.0.1")
ELASTIC_PORT = int(os.getenv("ELASTIC_PORT", 9200))
ELASTIC_FILM_INDEX = os.getenv("ELASTIC_FILM_INDEX", "movies")
ELASTIC_GENRE_INDEX = os.getenv("ELASTIC_GENRE_INDEX", "genres")
ELASTIC_PERSON_INDEX = os.getenv("ELASTIC_PERSON_INDEX", "persons")

OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "movies")
ENVIRONMENT = os.getenv("ENVIRONMENT", "test")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
OTEL_PYTHON_FASTAPI_EXCLUDED_URLS = os.getenv("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS", "")
AUTH_API_PUBLIC_KEY_URL = os.getenv("AUTH_API_PUBLIC_KEY_URL", "")
DEBUG = bool(os.getenv("DEBUG", ""))

# Корень проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOW_HOSTS = [h for h in os.getenv("ALLOW_HOSTS", "").split(",") if h]
ORIGINS = [o for o in os.getenv("ORIGINS", "").split(",") if o]
CACHE_EXPIRE = int(os.getenv("CACHE_EXPIRE", 600))
PAGINATION_DEFAULT_PAGE_SIZE = int(
    os.getenv("PAGINATION_DEFAULT_PAGE_SIZE", 50)
)
PAGINATION_MAX_PAGE_SIZE = int(os.getenv("PAGINATION_MAX_PAGE_SIZE", 100))
EXCLUDED_PATHS = {"/health", "/api/openapi", "/api/openapi.json"}
