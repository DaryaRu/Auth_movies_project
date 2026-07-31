"""
Benchmark-скрипт для тестирования производительности MongoDB.

Поддерживаемые режимы:
  1. Тест записи без нагрузки (INSERT)
  2. Тест чтения без нагрузки (SELECT Q1-Q4)
  3. Тест чтения с конкурентной нагрузкой (SELECT при активных INSERT)
  4. Тест чтения в реальном времени (измерение задержки появления данных)

Конфигурация берётся из файла .env в той же директории.

Использование:
    python benchmark_mongo.py
"""

import copy
import json
import os
import random
import statistics
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import BulkWriteError, DuplicateKeyError

# ----- PATHS -----
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(_SCRIPT_DIR, ".env")
DOCKER_COMPOSE_FILE = os.path.join(_SCRIPT_DIR, "docker-compose.benchmark.yml")
load_dotenv(ENV_PATH)


def wait_for_mongo_ready() -> bool:
    """
    Ожидает готовности MongoDB к подключениям.
    Возвращает True если база готова, False если таймаут.
    """
    print("Ожидание готовности MongoDB...")

    host = os.environ.get("MONGO_HOST", "127.0.0.1")
    port = int(os.environ.get("MONGO_PORT", "27017"))

    ready = False
    # Делаем 30 попыток с интервалом в 10 секунд (всего 5 минут)
    for _ in range(30):
        try:
            client: MongoClient[Any] = MongoClient[Any](f"mongodb://{host}:{port}/")
            client.admin.command("ping")
            client.close()
            ready = True
            print("  MongoDB полностью готова к работе!")
            break
        except Exception:
            print(".", end="", flush=True)
            time.sleep(10)

    if not ready:
        print("\n  Ошибка: MongoDB не успела запуститься за отведенное время.")
        return False

    return True


def start_docker_container() -> bool:
    """Запускает контейнер через docker compose."""
    print("\n[START] Поднимаем контейнер MongoDB...")

    # Проверяем, есть ли локальный образ
    try:
        result = subprocess.run(
            ["docker", "images", "-q", "mongo:latest"],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout.strip():
            print("  Локальный образ mongo:latest найден - используем его")
        else:
            print(
                "  Локальный образ не найден - "
                "docker compose скачает его автоматически"
            )
    except subprocess.CalledProcessError:
        print("  Не удалось проверить наличие локального образа")

    # Запускаем контейнер
    subprocess.run(
        ["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "up", "-d"],
        check=True,
        cwd=_SCRIPT_DIR,
    )
    print("  Контейнер запущен")

    return wait_for_mongo_ready()


def stop_docker_container() -> None:
    """Останавливает и удаляет контейнер через docker compose."""
    print("\n[STOP] Останавливаем контейнер MongoDB...")
    subprocess.run(
        ["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "down"],
        cwd=_SCRIPT_DIR,
        check=True,
    )
    print("  Контейнер остановлен")


def clear_mongo_cache(client: MongoClient[Any]) -> None:
    """
    Очищает кэш MongoDB (WiredTiger cache) для честного бенчмарка.

    Метод:
    1. Выполняем fsyncUnlock для сброса кэша страниц
    2. Закрываем и пересоздаем соединения для сброса кэша на уровне клиента

    Примечание: Полностью очистить WiredTiger cache без перезапуска MongoDB
    невозможно, но мы можем минимизировать влияние кэша.
    """
    print("\n[CACHE] Очистка кэша MongoDB...")
    try:
        # Метод 1: Используем fsyncUnlock для сброса кэша
        db = get_database(client)
        try:
            # Пытаемся выполнить fsyncUnlock (требует прав администратора)
            admin_db = client.admin
            admin_db.command("fsyncUnlock")
            print("  Кэш MongoDB очищен (fsyncUnlock)")
        except Exception as e:
            print(f"  fsyncUnlock недоступен: {e}")

        # Метод 2: Сброс кэша через закрытие/открытие коллекций
        # Это помогает сбросить кэш планов запросов
        db.command({"planCacheClear": "likes"})
        db.command({"planCacheClear": "reviews"})
        db.command({"planCacheClear": "bookmarks"})
        print("  Кэш планов запросов очищен (planCacheClear)")

    except Exception as e:
        print(f"  Не удалось полностью очистить кэш MongoDB: {e}")
        print(
            "  Для более точных результатов рассмотрите перезапуск контейнера"
        )


@dataclass
class Config:
    """Централизованная конфигурация BenchMark-скрипта."""

    MONGO_HOST: str = os.environ.get("MONGO_HOST", "localhost")
    MONGO_PORT: int = int(os.environ.get("MONGO_PORT", "27017"))
    MONGO_DB: str = os.environ.get("MONGO_DB", "ugc")

    # Объем данных для каждого типа
    LIKES_ROWS: int = int(os.environ.get("LIKES_ROWS", "3500000"))
    REVIEWS_ROWS: int = int(os.environ.get("REVIEWS_ROWS", "3500000"))
    BOOKMARKS_ROWS: int = int(os.environ.get("BOOKMARKS_ROWS", "3500000"))

    BATCH_SIZE: int = int(os.environ.get("BATCH_SIZE", "1000"))
    THREADS: int = int(os.environ.get("THREADS", "4"))

    QUERY_RUNS: int = int(os.environ.get("QUERY_RUNS", "20"))

    CONCURRENT_WRITER_THREADS: int = int(
        os.environ.get("CONCURRENT_WRITER_THREADS", "4")
    )


config = Config()

# Генерируем пулы для реалистичных данных
POPULAR_FILMS = [str(uuid.uuid4()) for _ in range(1000)]
ACTIVE_USERS = [str(uuid.uuid4()) for _ in range(10000)]

# ---------------------------------------------------------------------------
# Вспомогательные структуры
# ---------------------------------------------------------------------------


@dataclass
class QueryResult:
    """Результат выполнения одного запроса."""

    name: str
    times: list[float] = field(default_factory=list)
    rows_read: int = 0
    rows_returned: int = 0

    @property
    def avg_time(self) -> float:
        return statistics.mean(self.times) if self.times else 0.0

    @property
    def min_time(self) -> float:
        return min(self.times) if self.times else 0.0

    @property
    def max_time(self) -> float:
        return max(self.times) if self.times else 0.0

    @property
    def median_time(self) -> float:
        return statistics.median(self.times) if self.times else 0.0


# ---------------------------------------------------------------------------
# Генерация данных для UGC
# ---------------------------------------------------------------------------
def generate_likes_batch(size: int) -> list[dict[str, Any]]:
    """Генерация пачки лайков."""
    batch: list[dict[str, Any]] = []
    base_date = datetime.now()

    ratings = random.choices(
        population=range(0, 11),
        weights=[1, 1, 2, 3, 5, 8, 10, 15, 20, 20, 15],
        k=size,
    )

    for i in range(size):
        user_id = (
            random.choice(ACTIVE_USERS)
            if random.random() > 0.01
            else str(uuid.uuid4())
        )
        film_id = (
            random.choice(POPULAR_FILMS)
            if random.random() > 0.01
            else str(uuid.uuid4())
        )

        batch.append(
            {
                "user_id": user_id,
                "film_id": film_id,
                "rating": ratings[i],
                "created_at": base_date
                - timedelta(
                    days=random.randint(0, 365),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                ),
            }
        )
    return batch


def generate_reviews_batch(size: int) -> list[dict[str, Any]]:
    """Генерация пачки рецензий."""
    batch: list[dict[str, Any]] = []
    base_date = datetime.now()

    ratings = random.choices(
        population=range(0, 11),
        weights=[1, 1, 2, 3, 5, 8, 10, 15, 20, 20, 15],
        k=size,
    )

    for i in range(size):
        batch.append(
            {
                "user_id": random.choice(ACTIVE_USERS),
                "film_id": random.choice(POPULAR_FILMS),
                "text": f"Отзыв о фильме {random.randint(1, 1000)}",
                "rating": ratings[i],
                "likes_count": random.randint(0, 100),
                "dislikes_count": random.randint(0, 50),
                "created_at": base_date
                - timedelta(
                    days=random.randint(0, 365),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                ),
            }
        )
    return batch


def generate_bookmarks_batch(size: int) -> list[dict[str, Any]]:
    """Генерация пачки закладок."""
    batch: list[dict[str, Any]] = []
    base_date = datetime.now()

    for _ in range(size):
        user_id = (
            random.choice(ACTIVE_USERS)
            if random.random() > 0.01
            else str(uuid.uuid4())
        )
        film_id = (
            random.choice(POPULAR_FILMS)
            if random.random() > 0.01
            else str(uuid.uuid4())
        )

        batch.append(
            {
                "user_id": user_id,
                "film_id": film_id,
                "created_at": base_date
                - timedelta(
                    days=random.randint(0, 365),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                ),
            }
        )
    return batch


# ---------------------------------------------------------------------------
# Подключение к MongoDB
# ---------------------------------------------------------------------------


def create_client() -> MongoClient[Any]:
    """Создаёт клиент MongoDB."""
    return MongoClient[Any](f"mongodb://{config.MONGO_HOST}:{config.MONGO_PORT}/")


def get_database(client: MongoClient[Any]) -> Database[Any]:
    """Получает базу данных."""
    return client[config.MONGO_DB]


# ---------------------------------------------------------------------------
# Подготовка schema
# ---------------------------------------------------------------------------


def setup_database_with_test_ids(client: MongoClient[Any]) -> tuple[str, str]:
    """Создаёт БД и коллекции для тестов, возвращает тестовые ID."""
    db = get_database(client)

    # Удаляем старые коллекции
    db.likes.drop()
    db.reviews.drop()
    db.bookmarks.drop()

    # Создаем коллекции
    likes_collection = db.likes
    reviews_collection = db.reviews
    bookmarks_collection = db.bookmarks

    # Создаем индексы для оптимизации запросов
    # Индексы для коллекции likes:
    # Одиночные индексы, вероятно, не нужны
    likes_collection.create_index("film_id")
    likes_collection.create_index([("film_id", 1), ("rating", 1)])
    likes_collection.create_index(
        [("user_id", 1), ("film_id", 1)], unique=True
    )
    likes_collection.create_index([("user_id", 1), ("rating", 1)])
    # Для Q3 (список лайков пользователя): составной индекс
    # user_id + created_at
    likes_collection.create_index([("user_id", 1), ("created_at", -1)])

    # Индексы для коллекции reviews:
    # Одиночные индексы, вероятно, не нужны
    reviews_collection.create_index("user_id")
    reviews_collection.create_index("film_id")
    reviews_collection.create_index("created_at")
    reviews_collection.create_index([("film_id", 1), ("created_at", -1)])
    reviews_collection.create_index([("user_id", 1), ("created_at", -1)])

    # Индексы для коллекции bookmarks:
    # Одиночные индексы, вероятно, не нужны
    bookmarks_collection.create_index("user_id")
    bookmarks_collection.create_index("film_id")
    bookmarks_collection.create_index(
        [("user_id", 1), ("film_id", 1)], unique=True
    )
    bookmarks_collection.create_index([("user_id", 1), ("created_at", -1)])

    test_user_id = str(uuid.uuid4())
    test_film_id = str(uuid.uuid4())

    # Вставляем тестовые данные в каждую коллекцию
    # Для likes
    for i in range(10):
        current_film = test_film_id if i == 0 else str(uuid.uuid4())
        likes_collection.insert_one(
            {
                "user_id": test_user_id,
                "film_id": current_film,
                "rating": random.randint(0, 10),
                "created_at": datetime.now()
                - timedelta(seconds=random.randint(0, 2592000)),
            }
        )

    # Для reviews
    for i in range(10):
        current_film = test_film_id if i == 0 else str(uuid.uuid4())
        reviews_collection.insert_one(
            {
                "user_id": test_user_id,
                "film_id": current_film,
                "text": f"Тестовый отзыв о фильме {random.randint(1, 1000)}",
                "rating": random.randint(0, 10),
                "likes_count": random.randint(0, 5),
                "dislikes_count": random.randint(0, 2),
                "created_at": datetime.now()
                - timedelta(seconds=random.randint(0, 2592000)),
            }
        )

    # Для bookmarks
    for _ in range(10):
        bookmarks_collection.insert_one(
            {
                "user_id": test_user_id,
                "film_id": str(uuid.uuid4()),
                "created_at": datetime.now()
                - timedelta(seconds=random.randint(0, 2592000)),
            }
        )

    print("  Коллекции likes, reviews, bookmarks созданы с индексами.")
    print(f"  Тестовый user_id: {test_user_id}")
    print(f"  Тестовый film_id: {test_film_id}")

    return test_user_id, test_film_id


# ---------------------------------------------------------------------------
# Запись данных
# ---------------------------------------------------------------------------


# Механизм retry с экспоненциальной задержкой
MAX_RETRY_ATTEMPTS = 5
RETRY_BASE_DELAY = 0.01  # 10 мс базовая задержка
RETRY_MAX_DELAY = 0.5  # 500 мс максимальная задержка


def insert_with_retry(
    collection: Any,
    batch: list[dict[str, Any]],
    collection_name: str = "",
    max_attempts: int = MAX_RETRY_ATTEMPTS,
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
) -> tuple[int, int]:
    """
    Вставляет пачку документов с механизмом retry при конфликтах.

    Args:
        collection: MongoDB коллекция
        batch: пачка документов для вставки
        collection_name: имя коллекции для логгирования
        max_attempts: максимальное количество попыток
        base_delay: базовая задержка между попытками
        max_delay: максимальная задержка

    Возвращает кортеж (успешно_вставлено, конфликтов).

    Логика:
    1. При BulkWriteError анализируем ошибки - разделяем успешные
       и конфликтующие документы
    2. Для конфликтующих регенерируем данные
       (новые user_id/film_id) и пробуем снова
    3. Используем экспоненциальную задержку между попытками
    """
    successful_count = 0
    conflict_count = 0

    for attempt in range(max_attempts):
        try:
            if not batch:
                break

            result = collection.insert_many(batch, ordered=False)
            successful_count += len(result.inserted_ids)
            break  # Успех, выходим из цикла retry

        except BulkWriteError as e:
            # Получаем детали ошибок
            write_errors = (
                e.details.get("writeErrors", []) if e.details else []
            )
            inserted_count = e.details.get("nInserted", 0) if e.details else 0

            # Считаем успешно вставленные
            successful_count += inserted_count

            # Определяем индексы конфликтующих документов
            conflict_indices = set()
            for err in write_errors:
                idx = err.get("index")
                if idx is not None:
                    conflict_indices.add(idx)

            if not conflict_indices and write_errors:
                conflict_indices = set(range(len(batch)))

            conflict_count += len(conflict_indices)

            new_batch = []
            for i, doc in enumerate(batch):
                if i in conflict_indices:
                    # Регенерируем конфликтующие поля
                    new_doc = doc.copy()
                    if random.random() > 0.5:
                        new_doc["user_id"] = str(uuid.uuid4())
                    if random.random() > 0.5:
                        new_doc["film_id"] = str(uuid.uuid4())
                    new_batch.append(new_doc)
            batch = new_batch

            # Экспоненциальная задержка перед следующей попыткой
            if batch and attempt < max_attempts - 1:
                delay = min(base_delay * (2**attempt), max_delay)
                # Добавляем джиттер для уменьшения коллизий между потоками
                jitter = random.uniform(0, delay * 0.3)
                time.sleep(delay + jitter)

        except DuplicateKeyError:
            # Все документы в пачке конфликтуют
            conflict_count += len(batch)

            if attempt < max_attempts - 1:
                # Регенерируем всю пачку
                new_batch = []
                for doc in batch:
                    new_doc = doc.copy()
                    if "user_id" in new_doc:
                        new_doc["user_id"] = str(uuid.uuid4())
                    if "film_id" in new_doc:
                        new_doc["film_id"] = str(uuid.uuid4())
                    new_batch.append(new_doc)
                batch = new_batch

                delay = min(base_delay * (2**attempt), max_delay)
                jitter = random.uniform(0, delay * 0.3)
                time.sleep(delay + jitter)
            else:
                break

    return successful_count, conflict_count


def writer_worker_likes(num_batches: int, batch_size: int) -> None:
    """Воркер для записи лайков с retry механизмом."""
    client = create_client()
    db = get_database(client)

    total_inserted = 0
    total_conflicts = 0

    for _i in range(num_batches):
        batch = generate_likes_batch(batch_size)
        inserted, conflicts = insert_with_retry(db.likes, batch, "Likes")
        total_inserted += inserted
        total_conflicts += conflicts

    print(
        f"  [Likes] Итого: вставлено={total_inserted}, "
        f"конфликтов={total_conflicts}"
    )
    client.close()


def writer_worker_reviews(num_batches: int, batch_size: int) -> None:
    """Воркер для записи рецензий с retry механизмом."""
    client = create_client()
    db = get_database(client)

    total_inserted = 0
    total_conflicts = 0

    for _i in range(num_batches):
        batch = generate_reviews_batch(batch_size)
        inserted, conflicts = insert_with_retry(db.reviews, batch, "Reviews")
        total_inserted += inserted
        total_conflicts += conflicts

    print(
        f"  [Reviews] Итого: вставлено={total_inserted}, "
        f"конфликтов={total_conflicts}"
    )
    client.close()


def writer_worker_bookmarks(num_batches: int, batch_size: int) -> None:
    """Воркер для записи закладок с retry механизмом."""
    client = create_client()
    db = get_database(client)

    total_inserted = 0
    total_conflicts = 0

    for _i in range(num_batches):
        batch = generate_bookmarks_batch(batch_size)
        inserted, conflicts = insert_with_retry(
            db.bookmarks, batch, "Bookmarks"
        )
        total_inserted += inserted
        total_conflicts += conflicts

    print(
        f"  [Bookmarks] Итого: вставлено={total_inserted}, "
        f"конфликтов={total_conflicts}"
    )
    client.close()


def run_write_test() -> tuple[float, float]:
    """
    Тест записи без нагрузки.
    Возвращает (total_time_sec, rows_per_sec).
    """
    print(f"\n{'=' * 60}")
    print("ТЕСТ ЗАПИСИ БЕЗ НАГРУЗКИ")
    print(
        f"  Likes: {config.LIKES_ROWS:_}, "
        f"Reviews: {config.REVIEWS_ROWS:_}, "
        f"Bookmarks: {config.BOOKMARKS_ROWS:_}"
    )
    print(f"  {config.BATCH_SIZE}/пачка, {config.THREADS} потоков")
    print(f"{'=' * 60}")

    likes_batches = config.LIKES_ROWS // config.BATCH_SIZE
    reviews_batches = config.REVIEWS_ROWS // config.BATCH_SIZE
    bookmarks_batches = config.BOOKMARKS_ROWS // config.BATCH_SIZE

    batches_per_thread_likes = likes_batches // config.THREADS
    batches_per_thread_reviews = reviews_batches // config.THREADS
    batches_per_thread_bookmarks = bookmarks_batches // config.THREADS

    start = time.time()

    with ThreadPoolExecutor(max_workers=config.THREADS) as executor:
        print(f"  Запись лайков ({likes_batches} пачек)...")
        futures = [
            executor.submit(
                writer_worker_likes,
                batches_per_thread_likes,
                config.BATCH_SIZE,
            )
            for _ in range(config.THREADS)
        ]
        for f in futures:
            f.result()
        print(f"    Лайки записаны за {time.time() - start:.2f} сек")

        print(f"  Запись рецензий ({reviews_batches} пачек)...")
        futures = [
            executor.submit(
                writer_worker_reviews,
                batches_per_thread_reviews,
                config.BATCH_SIZE,
            )
            for _ in range(config.THREADS)
        ]
        for f in futures:
            f.result()
        print(f"    Рецензии записаны за {time.time() - start:.2f} сек")

        print(f"  Запись закладок ({bookmarks_batches} пачек)...")
        futures = [
            executor.submit(
                writer_worker_bookmarks,
                batches_per_thread_bookmarks,
                config.BATCH_SIZE,
            )
            for _ in range(config.THREADS)
        ]
        for f in futures:
            f.result()
        print(f"    Закладки записаны за {time.time() - start:.2f} сек")

    elapsed = time.time() - start
    total_rows = (
        config.LIKES_ROWS + config.REVIEWS_ROWS + config.BOOKMARKS_ROWS
    )
    speed = total_rows / elapsed
    print(f"  Запись завершена за {elapsed:.2f} сек.")
    print(f"  Скорость: {speed:,.2f} строк/сек")
    print(f"  Итого записано: {total_rows:_} строк")
    return elapsed, speed


# ---------------------------------------------------------------------------
# SQL-запросы для тестов (MongoDB)
# ---------------------------------------------------------------------------
ANALYTIC_QUERIES: list[tuple[str, str, str, dict[str, Any]]] = [
    (
        "Q1: Средняя оценка фильма",
        "likes",
        "aggregate",
        {
            "pipeline": [
                {"$match": {"film_id": None}},
                {
                    "$group": {
                        "_id": "$film_id",
                        "avg_rating": {"$avg": "$rating"},
                        "rating_count": {"$sum": 1},
                    }
                },
            ]
        },
    ),
    (
        "Q2: Количество лайков и дизлайков у фильма",
        "likes",
        "aggregate",
        {
            "pipeline": [
                {"$match": {"film_id": None}},
                {
                    "$group": {
                        "_id": "$film_id",
                        "total_ratings": {"$sum": 1},
                        "likes_count": {
                            "$sum": {"$cond": [{"$gte": ["$rating", 7]}, 1, 0]}
                        },
                        "dislikes_count": {
                            "$sum": {"$cond": [{"$lte": ["$rating", 4]}, 1, 0]}
                        },
                    }
                },
            ]
        },
    ),
    (
        "Q3: Список понравившихся фильмов пользователя",
        "likes",
        "find",
        {"filter": {"user_id": None}, "sort": {"created_at": -1}, "limit": 50},
    ),
    (
        "Q4: Список закладок пользователя",
        "bookmarks",
        "find",
        {"filter": {"user_id": None}, "sort": {"created_at": -1}, "limit": 50},
    ),
]


# ---------------------------------------------------------------------------
# Выполнение запросов
# ---------------------------------------------------------------------------
def run_single_query(
    db: Database[Any],
    name: str,
    collection_name: str,
    query_type: str,
    query_config: dict[str, Any],
    runs: int,
    params: dict[str, Any] | None = None,
) -> QueryResult:
    """
    Выполняет один запрос N раз, собирает статистику.
    Возвращает QueryResult.

    Важно: кэш MongoDB очищается перед каждым прогоном для честных измерений.
    """
    result = QueryResult(name=name)
    collection = db[collection_name]

    for i in range(runs):
        # Очищаем кэш MongoDB перед прогоном для честных результатов
        # Это предотвращает занижение времени из-за кэширования данных
        clear_mongo_cache(db.client)

        start = time.time()

        if query_type == "aggregate":
            # Агрегация
            pipeline = query_config.get("pipeline", [])

            if params:
                param_value = params.get("film_id") or params.get("user_id")
                pipeline_str = json.dumps(pipeline)
                pipeline = json.loads(
                    pipeline_str.replace("None", json.dumps(param_value))
                )
            agg_cursor = collection.aggregate(pipeline)
            rows = list(agg_cursor)
        else:
            # Find
            filter_query = query_config.get("filter", {})
            if params:
                param_value = params.get("film_id") or params.get("user_id")
                filter_str = json.dumps(filter_query)
                filter_query = json.loads(
                    filter_str.replace("None", json.dumps(param_value))
                )

            sort = query_config.get("sort", {})
            limit = query_config.get("limit", 0)

            if sort:
                find_cursor = collection.find(filter_query).sort(
                    list(sort.items())
                )
            else:
                find_cursor = collection.find(filter_query)

            if limit:
                find_cursor = find_cursor.limit(limit)

            rows = list(find_cursor)

        elapsed = time.time() - start

        result.times.append(elapsed)
        result.rows_returned = len(rows)
        result.rows_read = len(rows)

        sys.stdout.write(f"\r  [{name}] Прогон {i + 1}/{runs}...")
        sys.stdout.flush()

    if result.rows_read == 0:
        result.rows_read = result.rows_returned

    print(f"  [{name}] готово.")
    return result


def run_read_tests(
    label: str = "БЕЗ НАГРУЗКИ",
    test_user_id: str | None = None,
    test_film_id: str | None = None,
) -> list[QueryResult]:
    """
    Запускает все аналитические запросы и возвращает результаты.
    """
    print(f"\n{'=' * 60}")
    print(f"  ТЕСТ ЧТЕНИЯ {label}")
    print(f"  {len(ANALYTIC_QUERIES)} запросов x {config.QUERY_RUNS} прогонов")
    print(f"{'=' * 60}")

    client = create_client()

    # Очищаем кэш MongoDB перед тестом для честных результатов
    clear_mongo_cache(client)

    db = get_database(client)
    results: list[QueryResult] = []

    for name, collection_name, query_type, query_config in ANALYTIC_QUERIES:
        # Определяем параметры для запроса
        params = None
        if "user_id" in str(query_config):
            params = {"user_id": test_user_id}
        elif "film_id" in str(query_config):
            params = {"film_id": test_film_id}

        qr = run_single_query(
            db,
            name,
            collection_name,
            query_type,
            query_config,
            config.QUERY_RUNS,
            params,
        )
        results.append(qr)

    client.close()
    return results


# ---------------------------------------------------------------------------
# Realtime-тест (измерение задержки появления данных)
# ---------------------------------------------------------------------------
def read_realtime() -> list[QueryResult]:
    """
    Измеряет задержку появления данных в реальном времени.
    Для каждого запроса:
    1. Выполняется запрос и сохраняется результат
    2. Вставляется новый документ с уникальным ID
    3. Измеряется время до появления этого документа в результатах
    """
    client = create_client()
    db = get_database(client)

    # Инициализируем результаты по одному на каждый запрос
    results: list[QueryResult] = [
        QueryResult(name=name) for name, _, _, _ in ANALYTIC_QUERIES
    ]

    for run in range(config.QUERY_RUNS):
        for query_idx, (
            name,
            collection_name,
            query_type,
            query_config,
        ) in enumerate(ANALYTIC_QUERIES):
            # Генерируем уникальные ID, чтобы избежать DuplicateKeyError
            test_user_id = str(uuid.uuid4())
            test_film_id = str(uuid.uuid4())

            collection = db[collection_name]

            start = time.time()

            base_date = datetime.now()

            if collection_name == "bookmarks":
                new_doc = {
                    "user_id": test_user_id,
                    "film_id": test_film_id,
                    "created_at": base_date,
                }
            elif collection_name == "likes":
                new_doc = {
                    "user_id": test_user_id,
                    "film_id": test_film_id,
                    "rating": random.randint(1, 10),
                    "created_at": base_date,
                }
            else:
                # reviews
                new_doc = {
                    "user_id": test_user_id,
                    "film_id": test_film_id,
                    "text": f"Тестовый отзыв {uuid.uuid4()}",
                    "rating": random.randint(1, 10),
                    "likes_count": random.randint(0, 5),
                    "dislikes_count": random.randint(0, 2),
                    "created_at": base_date,
                }

            collection.insert_one(new_doc)

            if query_type == "aggregate":
                ready_pipeline = copy.deepcopy(
                    query_config.get("pipeline", [])
                )
                for stage in ready_pipeline:
                    if "$match" in stage:
                        for key, value in stage["$match"].items():
                            if value is None or value == "$FILM_ID":
                                stage["$match"][key] = test_film_id
                            if value == "$USER_ID":
                                stage["$match"][key] = test_user_id
            else:
                ready_filter = copy.deepcopy(query_config.get("filter", {}))
                # Заменяем значения None на наш сгенерированный ID
                for key, value in ready_filter.items():
                    if value is None or value == "$USER_ID":
                        ready_filter[key] = test_user_id
                    elif value == "$FILM_ID":
                        ready_filter[key] = test_film_id

                sort = query_config.get("sort", {})
                limit = query_config.get("limit", 0)

            # Ждем появления документа в результатах
            timeout = 5.0
            poll_interval = 0.01
            found = False
            rows_after = []

            while (time.time() - start) < timeout:
                if query_type == "aggregate":
                    cursor: Any = collection.aggregate(ready_pipeline)
                else:
                    cursor = collection.find(ready_filter)
                    if sort:
                        cursor = cursor.sort(list(sort.items()))
                    if limit:
                        cursor = cursor.limit(limit)

                    rows_after = list(cursor)

                    if len(rows_after) > 0:
                        for row in rows_after:
                            if query_type == "aggregate":
                                if (
                                    row.get("_id") == test_film_id
                                    or row.get("film_id") == test_film_id
                                ):
                                    found = True
                                    break
                            else:
                                # Для find точечно проверяем film_id
                                if row.get("film_id") == test_film_id:
                                    found = True
                                    break

                    if found:
                        break

                    time.sleep(poll_interval)

            elapsed = time.time() - start

            # Добавляем результат в существующий QueryResult для этого запроса
            result = results[query_idx]
            result.times.append(elapsed)
            result.rows_returned = len(rows_after)
            result.rows_read = len(rows_after)

            status = "OK" if found else "TIMEOUT"
            sys.stdout.write(
                f"\r  [{name}] Прогон {run + 1}/{config.QUERY_RUNS}... "
                f"latency={elapsed * 1000:.1f}мс [{status}]"
            )
            sys.stdout.flush()

        print()
    client.close()
    return results


def run_realtime_test() -> list[QueryResult]:
    """
    Тест задержки появления данных в реальном времени.
    """
    print(f"\n{'=' * 60}")
    print("ТЕСТ ЧТЕНИЯ В РЕАЛЬНОМ ВРЕМЕНИ")
    print(f"  {len(ANALYTIC_QUERIES)} запросов x {config.QUERY_RUNS} прогонов")
    print(f"{'=' * 60}")

    results: list[QueryResult] = read_realtime()

    print("\n  Тест реального времени завершен.")
    return results


# ---------------------------------------------------------------------------
# Concurrent-тест (чтение при активной записи)
# ---------------------------------------------------------------------------
def _continuous_writer_likes(stop_event: threading.Event) -> None:
    """Бесконечно вставляет лайки пока stop_event не установлен."""
    client = create_client()
    db = get_database(client)

    while not stop_event.is_set():
        try:
            batch = generate_likes_batch(config.BATCH_SIZE // 3)
            insert_with_retry(db.likes, batch, max_attempts=3)
        except Exception:
            pass  # Игнорируем ошибки в фоновом писателе

    client.close()


def _continuous_writer_reviews(stop_event: threading.Event) -> None:
    """Бесконечно вставляет рецензии пока stop_event не установлен."""
    client = create_client()
    db = get_database(client)

    while not stop_event.is_set():
        try:
            batch = generate_reviews_batch(config.BATCH_SIZE // 3)
            insert_with_retry(db.reviews, batch, max_attempts=3)
        except Exception:
            pass  # Игнорируем ошибки в фоновом писателе

    client.close()


def _continuous_writer_bookmarks(stop_event: threading.Event) -> None:
    """Бесконечно вставляет закладки пока stop_event не установлен."""
    client = create_client()
    db = get_database(client)

    while not stop_event.is_set():
        try:
            batch = generate_bookmarks_batch(config.BATCH_SIZE // 3)
            insert_with_retry(db.bookmarks, batch, max_attempts=3)
        except Exception:
            pass  # Игнорируем ошибки в фоновом писателе

    client.close()


def run_concurrent_read_test(
    test_user_id: str | None = None,
    test_film_id: str | None = None,
) -> list[QueryResult]:
    """
    Измеряет время выполнения запросов при активной фоновой записи.
    Для каждого запроса выполняется N прогонов с измерением времени.
    """
    print(f"\n{'=' * 60}")
    print("ТЕСТ ЧТЕНИЯ С КОНКУРЕНТНОЙ НАГРУЗКОЙ")
    print(f"  {config.CONCURRENT_WRITER_THREADS} фоновых писателей")
    print(f"  {len(ANALYTIC_QUERIES)} запросов x {config.QUERY_RUNS} прогонов")
    print(f"{'=' * 60}")

    # Запускаем фоновых писателей
    stop_event = threading.Event()
    writers: list[threading.Thread] = []

    for i in range(config.CONCURRENT_WRITER_THREADS):
        if i % 3 == 0:
            t = threading.Thread(
                target=_continuous_writer_likes,
                args=(stop_event,),
                daemon=True,
            )
        elif i % 3 == 1:
            t = threading.Thread(
                target=_continuous_writer_reviews,
                args=(stop_event,),
                daemon=True,
            )
        else:
            t = threading.Thread(
                target=_continuous_writer_bookmarks,
                args=(stop_event,),
                daemon=True,
            )
        t.start()
        writers.append(t)
        print(f"  Старт фонового писателя #{i + 1}")

    time.sleep(2)

    client = create_client()
    clear_mongo_cache(client)

    db = get_database(client)
    results: list[QueryResult] = []

    for name, collection_name, query_type, query_config in ANALYTIC_QUERIES:
        params = None
        if "user_id" in str(query_config):
            params = {"user_id": test_user_id}
        elif "film_id" in str(query_config):
            params = {"film_id": test_film_id}

        qr = run_single_query(
            db,
            name,
            collection_name,
            query_type,
            query_config,
            config.QUERY_RUNS,
            params,
        )
        results.append(qr)

    client.close()

    # Останавливаем писателей
    print("\n  Остановка фоновых писателей...")
    stop_event.set()
    for t in writers:
        t.join(timeout=5)

    print("  Concurrent тест завершен.")
    return results


# ---------------------------------------------------------------------------
# Формирование отчёта
# ---------------------------------------------------------------------------
def generate_report(
    write_time: float,
    write_speed: float,
    read_results: list[QueryResult],
    concurrent_results: list[QueryResult],
    realtime_results: list[QueryResult],
) -> str:
    """Генерирует текстовый отчёт и возвращает его."""
    threshold = 0.2  # 200 мс - требование производительности
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []

    def w(line: str = "") -> None:
        lines.append(line)

    # === ШАПКА ===
    w("=" * 64)
    w("       ОТЧЁТ О ТЕСТИРОВАНИИ ПРОИЗВОДИТЕЛЬНОСТИ")
    w("=" * 64)
    w()
    w(f"  Дата запуска:              {now}")
    w(f"  Целевой хост (ВМ):         {config.MONGO_HOST}:{config.MONGO_PORT}")
    w(f"  База данных:               {config.MONGO_DB}")
    total_data_rows = (
        config.LIKES_ROWS + config.REVIEWS_ROWS + config.BOOKMARKS_ROWS
    )
    w(
        f"  Объём данных: {total_data_rows:_} строк "
        f"(Likes: {config.LIKES_ROWS:_}, Reviews: {config.REVIEWS_ROWS:_}, "
        f"Bookmarks: {config.BOOKMARKS_ROWS:_})"
    )
    w()

    # === ЗАПИСЬ ===
    w("-" * 64)
    w("  РЕЗУЛЬТАТЫ ЗАПИСИ (INSERT)")
    w("-" * 64)
    w(f"  Общее время вставки:   {write_time:>12.2f} сек")
    w(f"  Итоговая скорость:     {write_speed:>12,.2f} строк/сек")
    w()

    # === ЧТЕНИЕ БЕЗ НАГРУЗКИ ===
    w("-" * 64)
    w("  РЕЗУЛЬТАТЫ ЧТЕНИЯ БЕЗ НАГРУЗКИ")
    w("-" * 64)
    w(f"  {'Запрос':<50} {'Avg':>7} {'Min':>7} {'Max':>7} {'Status':>6}")
    w("  " + "-" * 75)
    for qr in read_results:
        short = qr.name[:48]
        status = "PASS" if qr.avg_time <= threshold else "FAIL"
        w(
            f"  {short:<50} "
            f"{qr.avg_time:>7.4f} {qr.min_time:>7.4f} {qr.max_time:>7.4f} "
            f"{status:>6}"
        )
    w()

    # === ЧТЕНИЕ С НАГРУЗКОЙ ===
    w("-" * 64)
    w("  РЕЗУЛЬТАТЫ ЧТЕНИЯ С КОНКУРЕНТНОЙ НАГРУЗКОЙ")
    w("-" * 64)
    w(
        f"  {'Запрос':<46} {'Avg':>7} {'Min':>7} "
        f"{'Max':>7} {'Deg%':>7} {'Status':>6}"
    )
    w("  " + "-" * 90)
    for i, qr in enumerate(concurrent_results):
        short = qr.name[:44]
        baseline = read_results[i].avg_time if i < len(read_results) else 0
        degrad = (
            ((qr.avg_time - baseline) / baseline * 100) if baseline > 0 else 0
        )
        status = "PASS" if qr.avg_time <= threshold else "FAIL"
        w(
            f"  {short:<46} "
            f"{qr.avg_time:>7.4f} {qr.min_time:>7.4f} {qr.max_time:>7.4f} "
            f"{degrad:>6.1f}% {status:>6}"
        )
    w()
    w("  Deg% — процент замедления запроса под нагрузкой.")
    w()

    # === ЧТЕНИЕ В РЕАЛЬНОМ ВРЕМЕНИ (ИНФОРМАЦИЯ) ===
    w("-" * 64)
    w("  РЕЗУЛЬТАТЫ ЧТЕНИЯ В РЕАЛЬНОМ ВРЕМЕНИ (ИНФОРМАЦИЯ)")
    w("-" * 64)
    w(f"  {'Запрос':<50} {'latency_ms':>12}")
    w("  " + "-" * 64)
    for qr in realtime_results:
        short = qr.name[:48]
        avg_latency_ms = qr.avg_time * 1000
        w(f"  {short:<50} {avg_latency_ms:>12.1f}")
    w()
    w("  latency_ms — время появления данных после вставки (мс)")
    w("  Примечание: данные тесты не влияют на общий вердикт")
    w()

    # === ПРОВЕРКА ТРЕБОВАНИЯ < 200 МС ===
    w("=" * 64)
    w("  ПРОВЕРКА ТРЕБОВАНИЯ: обработка запроса < 200 мс")
    w("=" * 64)
    w()

    fails_no_load = [qr for qr in read_results if qr.avg_time > threshold]
    fails_concurrent = [
        qr for qr in concurrent_results if qr.avg_time > threshold
    ]

    # Без нагрузки
    w("  БЕЗ НАГРУЗКИ (порог < 200 мс):")
    all_pass_no_load = True
    for qr in read_results:
        if qr.avg_time <= threshold:
            status_str = f"PASS ({qr.avg_time * 1000:.1f}мс)"
        else:
            status_str = (
                f"FAIL ({qr.avg_time * 1000:.1f}мс > {threshold * 1000}мс)"
            )
        if qr.avg_time > threshold:
            all_pass_no_load = False
        w(f"    {qr.name:<50} [{status_str}]")
    w()

    # С нагрузкой
    w("  С КОНКУРЕНТНОЙ НАГРУЗКОЙ (порог < 200 мс):")
    all_pass_concurrent = True
    for qr in concurrent_results:
        if qr.avg_time <= threshold:
            status_str = f"PASS ({qr.avg_time * 1000:.1f}мс)"
        else:
            status_str = (
                f"FAIL ({qr.avg_time * 1000:.1f}мс > {threshold * 1000}мс)"
            )
        if qr.avg_time > threshold:
            all_pass_concurrent = False
        w(f"    {qr.name:<50} [{status_str}]")
    w()

    # === ОБЩИЙ ВЕРДИКТ ===
    w("-" * 64)
    w("  ОБЩИЙ ВЕРДИКТ")
    w("-" * 64)

    # Проверяем только два условия (realtime не влияет)
    all_pass = all_pass_no_load and all_pass_concurrent

    if all_pass:
        w("  [PASS] ВСЕ ЗАПРОСЫ ПРОХОДЯТ (< 200 мс)")
        w("  MongoDB удовлетворяет требованию по скорости")
        w("  обработки запросов.")
    elif all_pass_no_load and not all_pass_concurrent:
        w("  [WARN] Без нагрузки все запросы проходят,")
        w(
            f"         но {len(fails_concurrent)} запрос(ов) НЕ "
            f"проходят при нагрузке."
        )
        w("  Рекомендуется оптимизировать индексы или увеличить ресурсы.")
    elif not all_pass_no_load and all_pass_concurrent:
        w("  [WARN] Без нагрузки НЕ проходят запросы,")
        w("         но с нагрузкой все проходят (возможно, кэширование).")
        w("  Рекомендуется повторить тест без кэша.")
    else:
        w("  [FAIL] ТРЕБОВАНИЕ НЕ ВЫПОЛНЕНО.")
        w(
            f"         Без нагрузки: {len(fails_no_load)} не проходит "
            f"(< 200 мс)"
        )
        w(
            f"         С нагрузкой: {len(fails_concurrent)} не проходит "
            f"(< 200 мс)"
        )
        w(
            "  Рекомендуется пересмотреть схему или "
            "использовать другое хранилище."
        )
    w()

    if fails_no_load:
        w("  Запросы, не прошедшие тест БЕЗ нагрузки:")
        for qr in fails_no_load:
            w(f"    - {qr.name}: avg={qr.avg_time * 1000:.1f}мс")
    if fails_concurrent:
        w("  Запросы, не прошедшие тест С НАГРУЗКОЙ:")
        for qr in fails_concurrent:
            w(f"    - {qr.name}: avg={qr.avg_time * 1000:.1f}мс")
    w()

    w("=" * 64)
    w()

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Главный entry point
# ---------------------------------------------------------------------------
def run_benchmark() -> None:
    """Главная функция бенчмарка."""
    print("=" * 60)
    print("  MongoDB Benchmark")
    print(f"  Хост: {config.MONGO_HOST}:{config.MONGO_PORT}")
    print(f"  БД:   {config.MONGO_DB}")
    print("=" * 60)

    # 1. Setup
    print("\n[1/4] Подготовка базы данных...")
    client = create_client()
    test_user_id, test_film_id = setup_database_with_test_ids(client)
    client.close()

    # 2. Тест записи
    write_time, write_speed = run_write_test()

    # 3. Тест чтения без нагрузки (кэш очищается внутри функции)
    read_results = run_read_tests(
        label="БЕЗ НАГРУЗКИ",
        test_user_id=test_user_id,
        test_film_id=test_film_id,
    )

    # 4. Тест чтения с конкурентной нагрузкой
    # (кэш очищается внутри функции)
    concurrent_results = run_concurrent_read_test(test_user_id, test_film_id)

    # 5. Тест чтения в реальном времени:
    # измеряем задержку появления новых данных
    realtime_results = run_realtime_test()

    # 7. Генерация и сохранение отчёта
    print("\n[6/6] Генерация отчёта...")
    report = generate_report(
        write_time,
        write_speed,
        read_results,
        concurrent_results,
        realtime_results,
    )

    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "MONGO_BENCHMARK_REPORT.txt",
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"  Отчёт сохранён: {os.path.abspath(report_path)}")

    # Очистка
    client = create_client()
    db = get_database(client)
    db.likes.drop()
    db.reviews.drop()
    db.bookmarks.drop()
    client.close()
    print("  Временные коллекции удалены.")

    # Вывод вердикта в консоль
    print("\n" + report)


def main() -> None:
    """Точка входа с управлением контейнером."""
    # Поднимаем контейнер
    if not start_docker_container():
        print("\n[ERROR] Не удалось запустить MongoDB. Выход.")
        sys.exit(1)

    try:
        run_benchmark()
    finally:
        stop_docker_container()


if __name__ == "__main__":
    main()
