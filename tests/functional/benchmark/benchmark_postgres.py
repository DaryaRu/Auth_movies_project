"""
Benchmark-скрипт для тестирования производительности PostgreSQL.

Поддерживаемые режимы:
  1. Тест записи без нагрузки (INSERT)
  2. Тест чтения без нагрузки (SELECT Q1-Q4)
  3. Тест чтения с конкурентной нагрузкой (SELECT при активных INSERT)
  4. Тест чтения в реальном времени (измерение задержки появления данных)

Конфигурация берётся из файла .env в той же директории.

Использование:
    python benchmark_postgres.py
"""

import contextlib
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
from typing import Any, Optional, Tuple

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# ----- PATHS -----
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(_SCRIPT_DIR, ".env")
DOCKER_COMPOSE_FILE = os.path.join(
    _SCRIPT_DIR, "docker-compose.benchmark.yml"
)
load_dotenv(ENV_PATH)


def wait_for_postgres_ready() -> bool:
    """
    Ожидает готовности PostgreSQL к подключениям.
    Возвращает True если база готова, False если таймаут.
    """
    print("Ожидание готовности PostgreSQL...")

    conn_info = {
        "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "port": os.environ.get("POSTGRES_PORT", "5432"),
        "user": os.environ.get("POSTGRES_USER", "postgres"),
        "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "dbname": os.environ.get("POSTGRES_DB", "postgres"),
    }

    ready = False
    # Делаем 30 попыток с интервалом в 10 секунд (всего 5 минут)
    for _ in range(30):
        try:
            conn = psycopg2.connect(**conn_info)
            conn.close()
            ready = True
            print("  PostgreSQL полностью готова к работе!")
            break
        except Exception:
            print(".", end="", flush=True)
            time.sleep(10)

    if not ready:
        print(
            "\n  Ошибка: PostgreSQL не успела запуститься за отведенное время."
        )
        return False

    return True


def start_docker_container() -> bool:
    """Запускает контейнер через docker compose."""
    print("\n[START] Поднимаем контейнер PostgreSQL...")

    # Проверяем, есть ли локальный образ
    try:
        result = subprocess.run(
            ["docker", "images", "-q", "postgres:17"],
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout.strip():
            print("  Локальный образ postgres:17 найден - используем его")
        else:
            print(
                "  Локальный образ не найден - docker compose "
                "скачает его автоматически"
            )
    except subprocess.CalledProcessError:
        print("  Не удалось проверить наличие локального образа")

    # Запускаем контейнер
    subprocess.run(
        ["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "up", "-d"],
        check=True,
        cwd=_SCRIPT_DIR
    )
    print("  Контейнер запущен")

    # Ждем готовности PostgreSQL
    return wait_for_postgres_ready()


def stop_docker_container() -> None:
    """Останавливает и удаляет контейнер через docker compose."""
    print("\n[STOP] Останавливаем контейнер PostgreSQL...")
    subprocess.run(
        ["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "down"],
        cwd=_SCRIPT_DIR,
        check=True
    )
    print("  Контейнер остановлен")


def clear_postgres_cache(conn: psycopg2.extensions.connection) -> None:
    """
    Очищает кэш PostgreSQL (shared_buffers) для честного бенчмарка.
    
    Метод:
    1. Выполняем CHECKPOINT чтобы записать все грязные страницы на диск
    2. Выполняем COMMIT чтобы завершить транзакцию
    3. Выполняем DISCARD ALL для сброса сессионного кэша (требует autocommit)
    """
    print("\n[CACHE] Очистка кэша PostgreSQL...")
    cursor = conn.cursor()
    try:
        cursor.execute("CHECKPOINT")
        conn.commit()
        
        # Включаем autocommit для DISCARD ALL, так как эта команда не может
        # выполняться в транзакции
        old_autocommit = conn.autocommit
        conn.autocommit = True
        try:
            cursor.execute("DISCARD ALL")
        finally:
            conn.autocommit = old_autocommit
        
        print("  Кэш PostgreSQL очищен (CHECKPOINT + DISCARD ALL)")
    except Exception as e:
        print(f"  Не удалось полностью очистить кэш PostgreSQL: {e}")
    finally:
        cursor.close()


@dataclass
class Config:
    """Централизованная конфигурация BenchMark-скрипта."""
    POSTGRES_HOST: str = os.environ.get("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.environ.get("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.environ.get("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.environ.get("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.environ.get("POSTGRES_DB", "postgres")

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
    bytes_read: int = 0
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

# ---------------------------------------------------------------------------
# Генерация данных для UGC
# ---------------------------------------------------------------------------
def generate_likes_batch(
    size: int,
    user_pool: Optional[list[str]] = None
) -> list[Tuple[Any, ...]]:
    """
    Генерация пачки лайков в виде кортежей для Postgres.

    Args:
        size: Размер батча
        user_pool: Пул user_id для выбора
            (если None, используется ACTIVE_USERS)
    """
    batch: list[Tuple[Any, ...]] = []
    base_date = datetime.now()
    
    users = user_pool if user_pool else ACTIVE_USERS
    if not users:
        users = ACTIVE_USERS

    ratings = random.choices(
        population=range(0, 11),
        weights=[1, 1, 2, 3, 5, 8, 10, 15, 20, 20, 15],
        k=size
    )

    for _ in range(size):
        if random.random() > 0.01:
            user_id = random.choice(users)
        else:
            user_id = str(uuid.uuid4())
        if random.random() > 0.01:
            film_id = random.choice(POPULAR_FILMS)
        else:
            film_id = str(uuid.uuid4())
        
        batch.append((
            user_id,
            film_id,
            ratings[random.randint(0, size - 1)],
            base_date - timedelta(
                days=random.randint(0, 365),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
        ))
    return batch


def generate_reviews_batch(size: int) -> list[Tuple[Any, ...]]:
    """Генерация пачки рецензий."""
    batch: list[Tuple[Any, ...]] = []
    base_date = datetime.now()

    ratings = random.choices(
        population=range(0, 11),
        weights=[1, 1, 2, 3, 5, 8, 10, 15, 20, 20, 15],
        k=size
    )

    for i in range(size):
        batch.append((
            random.choice(ACTIVE_USERS),
            random.choice(POPULAR_FILMS),
            f"Отзыв о фильме {random.randint(1, 1000)}",
            ratings[i],
            random.randint(0, 100),
            random.randint(0, 50),
            base_date - timedelta(
                days=random.randint(0, 365),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
        ))
    return batch


def generate_bookmarks_batch(
    size: int,
    user_pool: Optional[list[str]] = None
) -> list[Tuple[Any, ...]]:
    """
    Генерация пачки закладок.

    Args:
        size: Размер батча
        user_pool: Пул user_id для выбора
            (если None, используется ACTIVE_USERS)
    """
    batch: list[Tuple[Any, ...]] = []
    base_date = datetime.now()
    
    users = user_pool if user_pool else ACTIVE_USERS
    if not users:
        users = ACTIVE_USERS

    for _ in range(size):
        if random.random() > 0.01:
            user_id = random.choice(users)
        else:
            user_id = str(uuid.uuid4())
        if random.random() > 0.01:
            film_id = random.choice(POPULAR_FILMS)
        else:
            film_id = str(uuid.uuid4())

        batch.append((
            user_id,
            film_id,
            base_date - timedelta(
                days=random.randint(0, 365),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
        ))
    return batch


# ---------------------------------------------------------------------------
# Генерация уникальных данных для concurrent-теста
# ---------------------------------------------------------------------------
# Счётчики для генерации уникальных комбинаций (user_id, film_id)
_likes_counter = 0
_reviews_counter = 0
_bookmarks_counter = 0
_counter_lock = threading.Lock()


def generate_likes_batch_unique(
    size: int,
    force_unique: bool = False
) -> list[Tuple[Any, ...]]:
    """
    Генерация пачки лайков с гарантированно уникальными
    комбинациями (user_id, film_id).

    Args:
        size: Размер батча
        force_unique: Если True, использует глобальный счётчик
            для 100% уникальности
    """
    global _likes_counter
    batch: list[Tuple[Any, ...]] = []
    base_date = datetime.now()

    with _counter_lock:
        for i in range(size):
            counter = _likes_counter + i
            user_id = ACTIVE_USERS[counter % len(ACTIVE_USERS)]
            film_idx = (counter // len(ACTIVE_USERS)) % len(POPULAR_FILMS)
            film_id = POPULAR_FILMS[film_idx]

            max_combinations = len(ACTIVE_USERS) * len(POPULAR_FILMS)
            if force_unique or counter >= max_combinations:
                user_id = str(uuid.uuid4())

            rating = random.randint(0, 10)
            created_at = base_date - timedelta(
                days=random.randint(0, 365),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            batch.append((user_id, film_id, rating, created_at))

        _likes_counter += size

    return batch


def generate_reviews_batch_unique(
    size: int,
    force_unique: bool = False
) -> list[Tuple[Any, ...]]:
    """
    Генерация пачки рецензий с гарантированно уникальными
    комбинациями (user_id, film_id).

    Args:
        size: Размер батча
        force_unique: Если True, использует глобальный счётчик
            для 100% уникальности
    """
    global _reviews_counter
    batch: list[Tuple[Any, ...]] = []
    base_date = datetime.now()

    ratings = random.choices(
        population=range(0, 11),
        weights=[1, 1, 2, 3, 5, 8, 10, 15, 20, 20, 15],
        k=size
    )

    with _counter_lock:
        for i in range(size):
            counter = _reviews_counter + i
            user_id = ACTIVE_USERS[counter % len(ACTIVE_USERS)]
            film_idx = (counter // len(ACTIVE_USERS)) % len(POPULAR_FILMS)
            film_id = POPULAR_FILMS[film_idx]

            max_combinations = len(ACTIVE_USERS) * len(POPULAR_FILMS)
            if force_unique or counter >= max_combinations:
                user_id = str(uuid.uuid4())

            text = f"Отзыв о фильме {counter}"
            rating = ratings[i]
            likes_count = random.randint(0, 100)
            dislikes_count = random.randint(0, 50)
            created_at = base_date - timedelta(
                days=random.randint(0, 365),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            batch.append((
                user_id, film_id, text, rating,
                likes_count, dislikes_count, created_at
            ))

        _reviews_counter += size

    return batch


def generate_bookmarks_batch_unique(
    size: int,
    force_unique: bool = False
) -> list[Tuple[Any, ...]]:
    """
    Генерация пачки закладок с гарантированно уникальными
    комбинациями (user_id, film_id).

    Args:
        size: Размер батча
        force_unique: Если True, использует глобальный счётчик
            для 100% уникальности
    """
    global _bookmarks_counter
    batch: list[Tuple[Any, ...]] = []
    base_date = datetime.now()

    with _counter_lock:
        for i in range(size):
            counter = _bookmarks_counter + i
            user_id = ACTIVE_USERS[counter % len(ACTIVE_USERS)]
            film_idx = (counter // len(ACTIVE_USERS)) % len(POPULAR_FILMS)
            film_id = POPULAR_FILMS[film_idx]

            max_combinations = len(ACTIVE_USERS) * len(POPULAR_FILMS)
            if force_unique or counter >= max_combinations:
                user_id = str(uuid.uuid4())

            created_at = base_date - timedelta(
                days=random.randint(0, 365),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
 
            batch.append((user_id, film_id, created_at))

        _bookmarks_counter += size

    return batch


# ---------------------------------------------------------------------------
# Подключение к PostgreSQL
# ---------------------------------------------------------------------------
def create_connection() -> psycopg2.extensions.connection:
    """Создаёт соединение с PostgreSQL."""
    conn = psycopg2.connect(
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        user=config.POSTGRES_USER,
        password=config.POSTGRES_PASSWORD,
        dbname=config.POSTGRES_DB,
    )
    conn.autocommit = False
    return conn


# ---------------------------------------------------------------------------
# Подготовка таблицы и схемы
# ---------------------------------------------------------------------------
def setup_database_with_test_ids() -> tuple[str, str]:
    """Создаёт БД и таблицы для тестов, возвращает тестовые ID."""
    conn = create_connection()
    cursor = conn.cursor()

    # Удаляем старые таблицы
    cursor.execute("DROP TABLE IF EXISTS likes CASCADE")
    cursor.execute("DROP TABLE IF EXISTS reviews CASCADE")
    cursor.execute("DROP TABLE IF EXISTS bookmarks CASCADE")

    # Создаем таблицу likes
    cursor.execute("""
        CREATE TABLE likes (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL,
            film_id UUID NOT NULL,
            rating SMALLINT NOT NULL CHECK (rating >= 0 AND rating <= 10),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    cursor.execute("CREATE INDEX idx_likes_film_id ON likes(film_id)")
    cursor.execute(
        "CREATE INDEX idx_likes_film_rating ON likes(film_id, rating)"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX idx_likes_user_film ON likes(user_id, film_id)"
    )
    cursor.execute(
        "CREATE INDEX idx_likes_user_rating ON likes(user_id, rating)"
    )
    cursor.execute(
        "CREATE INDEX idx_likes_user_created "
        "ON likes(user_id, created_at DESC)"
    )

    # Создаем таблицу reviews
    cursor.execute("""
        CREATE TABLE reviews (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL,
            film_id UUID NOT NULL,
            text TEXT NOT NULL,
            rating SMALLINT NOT NULL CHECK (rating >= 0 AND rating <= 10),
            likes_count INTEGER DEFAULT 0,
            dislikes_count INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    cursor.execute("CREATE INDEX idx_reviews_user_id ON reviews(user_id)")
    cursor.execute("CREATE INDEX idx_reviews_film_id ON reviews(film_id)")
    cursor.execute(
        "CREATE INDEX idx_reviews_created_at ON reviews(created_at)"
    )
    cursor.execute(
        "CREATE INDEX idx_reviews_film_created "
        "ON reviews(film_id, created_at DESC)"
    )
    cursor.execute(
        "CREATE INDEX idx_reviews_user_created "
        "ON reviews(user_id, created_at DESC)"
    )

    # Создаем таблицу bookmarks
    cursor.execute("""
        CREATE TABLE bookmarks (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL,
            film_id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    cursor.execute("CREATE INDEX idx_bookmarks_user_id ON bookmarks(user_id)")
    cursor.execute("CREATE INDEX idx_bookmarks_film_id ON bookmarks(film_id)")
    cursor.execute(
        "CREATE UNIQUE INDEX idx_bookmarks_user_film "
        "ON bookmarks(user_id, film_id)"
    )
    cursor.execute(
        "CREATE INDEX idx_bookmarks_user_created "
        "ON bookmarks(user_id, created_at DESC)"
    )

    test_user_id = str(uuid.uuid4())
    test_film_id = str(uuid.uuid4())

    for i in range(10):
        current_film = test_film_id if i == 0 else str(uuid.uuid4())
        insert_time = datetime.now() - timedelta(
            seconds=random.randint(0, 2592000)
        )
        cursor.execute(
            "INSERT INTO likes (user_id, film_id, rating, created_at) "
            "VALUES (%s, %s, %s, %s)",
            (test_user_id, current_film, random.randint(0, 10), insert_time)
        )

    for i in range(10):
        current_film = test_film_id if i == 0 else str(uuid.uuid4())
        insert_time = datetime.now() - timedelta(
            seconds=random.randint(0, 2592000)
        )
        cursor.execute(
            """
            INSERT INTO reviews (user_id, film_id, text, rating,
                                likes_count, dislikes_count, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                test_user_id,
                current_film,
                f"Тестовый отзыв о фильме {random.randint(1, 1000)}",
                random.randint(0, 10),
                random.randint(0, 5),
                random.randint(0, 2),
                insert_time
            )
        )

    for _ in range(10):
        insert_time = datetime.now() - timedelta(
            seconds=random.randint(0, 2592000)
        )
        cursor.execute(
            "INSERT INTO bookmarks (user_id, film_id, created_at) "
            "VALUES (%s, %s, %s)",
            (test_user_id, str(uuid.uuid4()), insert_time)
        )

    conn.commit()
    cursor.close()
    conn.close()

    print("  Таблицы likes, reviews, bookmarks созданы с индексами.")
    print(f"  Тестовый user_id: {test_user_id}")
    print(f"  Тестовый film_id: {test_film_id}")

    return test_user_id, test_film_id


# ---------------------------------------------------------------------------
# Запись данных
# ---------------------------------------------------------------------------
MAX_RETRY_ATTEMPTS = 5
RETRY_BASE_DELAY = 0.01
RETRY_MAX_DELAY = 0.5


def insert_with_retry(
    cursor: Any,
    conn: psycopg2.extensions.connection,
    insert_query: str,
    batch: list[Tuple[Any, ...]],
    collection_name: str = "",
    max_attempts: int = MAX_RETRY_ATTEMPTS,
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY
) -> Tuple[int, int]:
    """
    Вставляет пачку документов с механизмом retry при конфликтах.
    
    Args:
        cursor: Курсор базы данных
        conn: Соединение с базой данных
        insert_query: SQL-запрос INSERT
        batch: пачка документов для вставки
        collection_name: имя коллекции для логгирования
        max_attempts: максимальное количество попыток
        base_delay: базовая задержка между попытками
        max_delay: максимальная задержка
    
    Возвращает кортеж (успешно_вставлено, конфликтов).
    
    Логика:
    1. При IntegrityError разделяем успешные и конфликтующие документы
    2. Для конфликтующих регенерируем данные
        (новые user_id/film_id) и пробуем снова
    3. Используем экспоненциальную задержку между попытками
    """
    successful_count = 0
    conflict_count = 0
    remaining_batch = batch[:]
    
    for attempt in range(max_attempts):
        try:
            if not remaining_batch:
                break
                
            psycopg2.extras.execute_values(
                cursor, insert_query, remaining_batch
            )
            conn.commit()
            successful_count += len(remaining_batch)
            break
            
        except psycopg2.IntegrityError:
            conn.rollback()
            
            # Считаем конфликты - при IntegrityError все документы в батче
            # конфликтуют
            conflict_count += len(remaining_batch)
            
            # Регенерируем всю пачку с новыми ID
            new_batch = []
            for doc in remaining_batch:
                new_doc = list(doc)
                # doc[0] = user_id, doc[1] = film_id
                if len(new_doc) > 0:
                    new_doc[0] = str(uuid.uuid4())  # user_id
                if len(new_doc) > 1:
                    new_doc[1] = str(uuid.uuid4())  # film_id
                new_batch.append(tuple(new_doc))
            
            remaining_batch = new_batch
            
            # Экспоненциальная задержка перед следующей попыткой
            if remaining_batch and attempt < max_attempts - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = random.uniform(0, delay * 0.3)
                time.sleep(delay + jitter)
    
    return successful_count, conflict_count


def writer_worker_likes(
    num_batches: int,
    batch_size: int,
    thread_id: int = 0,
    total_threads: int = 1
) -> None:
    """Воркер для записи лайков с retry механизмом."""
    conn = create_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO likes (user_id, film_id, rating, created_at)
        VALUES %s
    """
    users_per_thread = len(ACTIVE_USERS) // total_threads
    slice_end = (thread_id + 1) * users_per_thread
    thread_users = ACTIVE_USERS[thread_id * users_per_thread: slice_end]

    if thread_id == total_threads - 1:
        thread_users = ACTIVE_USERS[thread_id * users_per_thread:]

    total_inserted = 0
    total_conflicts = 0
    
    for _ in range(num_batches):
        batch = generate_likes_batch(batch_size, user_pool=thread_users)
        inserted, conflicts = insert_with_retry(
            cursor, conn, query, batch, "Likes"
        )
        total_inserted += inserted
        total_conflicts += conflicts
    
    print(
        f"  [Likes] Итого: вставлено={total_inserted}, "
        f"конфликтов={total_conflicts}"
    )
    cursor.close()
    conn.close()


def writer_worker_reviews(num_batches: int, batch_size: int) -> None:
    """Воркер для записи рецензий с retry механизмом."""
    conn = create_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO reviews (user_id, film_id, text, rating,
                            likes_count, dislikes_count, created_at)
        VALUES %s
    """
    
    total_inserted = 0
    total_conflicts = 0
    
    for _ in range(num_batches):
        batch = generate_reviews_batch(batch_size)
        inserted, conflicts = insert_with_retry(
            cursor, conn, query, batch, "Reviews"
        )
        total_inserted += inserted
        total_conflicts += conflicts
    
    print(
        f"  [Reviews] Итого: вставлено={total_inserted}, "
        f"конфликтов={total_conflicts}"
    )
    cursor.close()
    conn.close()


def writer_worker_bookmarks(
    num_batches: int,
    batch_size: int,
    thread_id: int = 0,
    total_threads: int = 1
) -> None:
    """Воркер для записи закладок с retry механизмом."""
    conn = create_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO bookmarks (user_id, film_id, created_at) 
        VALUES %s
    """
    
    users_per_thread = len(ACTIVE_USERS) // total_threads
    start_idx = thread_id * users_per_thread
    if thread_id == total_threads - 1:
        end_idx = len(ACTIVE_USERS)
    else:
        end_idx = start_idx + users_per_thread
    
    thread_users = ACTIVE_USERS[start_idx:end_idx]
    
    total_inserted = 0
    total_conflicts = 0
    
    for _ in range(num_batches):
        batch = generate_bookmarks_batch(batch_size, user_pool=thread_users)
        inserted, conflicts = insert_with_retry(
            cursor, conn, query, batch, "Bookmarks"
        )
        total_inserted += inserted
        total_conflicts += conflicts
    
    print(
        f"  [Bookmarks] Итого: вставлено={total_inserted}, "
        f"конфликтов={total_conflicts}"
    )
    cursor.close()
    conn.close()


def run_write_test() -> tuple[float, float]:
    """
    Тест записи без нагрузки.
    Возвращает (total_time_sec, rows_per_sec).
    """
    print(f"\n{'=' * 60}")
    print("ТЕСТ ЗАПИСИ БЕЗ НАГРУЗКИ")
    print(f"  Likes: {config.LIKES_ROWS:_}, Reviews: {config.REVIEWS_ROWS:_}")
    print(f"  Bookmarks: {config.BOOKMARKS_ROWS:_}")
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
                writer_worker_likes, batches_per_thread_likes,
                config.BATCH_SIZE, thread_id=i, total_threads=config.THREADS
            )
            for i in range(config.THREADS)
        ]
        for f in futures:
            f.result()
        print(f"    Лайки записаны за {time.time() - start:.2f} сек")

        print(f"  Запись рецензий ({reviews_batches} пачек)...")
        futures = [
            executor.submit(
                writer_worker_reviews, batches_per_thread_reviews,
                config.BATCH_SIZE
            )
            for _ in range(config.THREADS)
        ]
        for f in futures:
            f.result()
        print(f"    Рецензии записаны за {time.time() - start:.2f} сек")
        
        print(f"  Запись закладок ({bookmarks_batches} пачек)...")

        futures = [
            executor.submit(
                writer_worker_bookmarks, batches_per_thread_bookmarks,
                config.BATCH_SIZE, thread_id=i, total_threads=config.THREADS
            )
            for i in range(config.THREADS)
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
# SQL-запросы для тестов (PostgreSQL)
# ---------------------------------------------------------------------------
ANALYTIC_QUERIES: list[Tuple[str, str, Tuple[Any, ...]]] = [
    (
        "Q1: Средняя оценка фильма",
        """
        SELECT film_id, AVG(rating) as avg_rating, COUNT(*) as rating_count
        FROM likes
        WHERE film_id = %s
        GROUP BY film_id
        """,
        ("film_id",),
    ),
    (
        "Q2: Количество лайков и дизлайков у фильма",
        """
        SELECT 
            film_id,
            COUNT(*) as total_ratings,
            SUM(CASE WHEN rating >= 7 THEN 1 ELSE 0 END) as likes_count,
            SUM(CASE WHEN rating <= 4 THEN 1 ELSE 0 END) as dislikes_count
        FROM likes
        WHERE film_id = %s
        GROUP BY film_id
        """,
        ("film_id",),
    ),
    (
        "Q3: Список понравившихся фильмов пользователя",
        """
        SELECT user_id, film_id, rating, created_at
        FROM likes
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 50
        """,
        ("user_id",),
    ),
    (
        "Q4: Список закладок пользователя",
        """
        SELECT user_id, film_id, created_at
        FROM bookmarks
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 50
        """,
        ("user_id",),
    ),
]


# ---------------------------------------------------------------------------
# Выполнение запросов
# ---------------------------------------------------------------------------
def run_single_query(
    conn: psycopg2.extensions.connection,
    name: str,
    sql: str,
    runs: int,
    params: Optional[Tuple[Any, ...]] = None,
) -> QueryResult:
    """
    Выполняет один запрос N раз, собирает статистику.
    Возвращает QueryResult.
    
    Важно: кэш PostgreSQL очищается перед каждым прогоном
        для честных измерений.
    """
    result = QueryResult(name=name)
    cursor = conn.cursor()

    for i in range(runs):
        clear_postgres_cache(conn)
        
        start = time.time()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        elapsed = time.time() - start

        result.times.append(elapsed)
        result.rows_returned = len(rows)
        result.rows_read = len(rows)

        sys.stdout.write(f"\r  [{name}] Прогон {i + 1}/{runs}...")
        sys.stdout.flush()

    if result.rows_read == 0:
        result.rows_read = result.rows_returned

    print(f"  [{name}] готово.")
    cursor.close()
    return result


def run_read_tests(
    label: str = "БЕЗ НАГРУЗКИ",
    test_user_id: Optional[str] = None,
    test_film_id: Optional[str] = None
) -> list[QueryResult]:
    """
    Запускает все аналитические запросы и возвращает результаты.
    """
    print(f"\n{'=' * 60}")
    print(f"  ТЕСТ ЧТЕНИЯ {label}")
    n_queries = len(ANALYTIC_QUERIES)
    print(f"  {n_queries} запросов x {config.QUERY_RUNS} прогонов")
    print(f"{'=' * 60}")

    conn = create_connection()
    
    # Очищаем кэш PostgreSQL перед тестом для честных результатов
    clear_postgres_cache(conn)
    
    results: list[QueryResult] = []

    for name, sql, param_types in ANALYTIC_QUERIES:
        params = None
        if "user_id" in param_types:
            params = (test_user_id,)
        elif "film_id" in param_types:
            params = (test_film_id,)
        
        qr = run_single_query(conn, name, sql, config.QUERY_RUNS, params)
        results.append(qr)

    conn.close()
    return results


# ---------------------------------------------------------------------------
# Realtime-тест (измерение задержки появления данных)
# ---------------------------------------------------------------------------
def read_realtime(
    test_user_id: Optional[str] = None,
    test_film_id: Optional[str] = None
) -> list[QueryResult]:
    """
    Измеряет задержку появления данных в реальном времени.
    Для каждого запроса:
    1. Выполняется запрос и сохраняется результат
    2. Вставляется новый документ с уникальным ID
    3. Измеряется время до появления этого документа в результатах

    Args:
        test_user_id: Тестовый user_id (не используется,
            генерируются уникальные ID)
        test_film_id: Тестовый film_id (не используется,
            генерируются уникальные ID)
    """
    conn = create_connection()
    cursor = conn.cursor()
    
    results: list[QueryResult] = [
        QueryResult(name=name) for name, _, _ in ANALYTIC_QUERIES
    ]

    for run in range(config.QUERY_RUNS):
        for query_idx, (name, sql, param_types) in enumerate(ANALYTIC_QUERIES):
            new_user_id = str(uuid.uuid4())
            new_film_id = str(uuid.uuid4())
            
            base_date = datetime.now()

            try:
                if "bookmarks" in sql.lower():
                    cursor.execute(
                        "INSERT INTO bookmarks (user_id, film_id, created_at) "
                        "VALUES (%s, %s, %s)",
                        (new_user_id, new_film_id, base_date)
                    )
                elif "likes" in sql.lower():
                    cursor.execute(
                        "INSERT INTO likes (user_id, film_id, "
                        "rating, created_at) "
                        "VALUES (%s, %s, %s, %s)",
                        (
                            new_user_id, new_film_id,
                            random.randint(1, 10), base_date
                        )
                    )
                else:
                    # reviews
                    cursor.execute(
                        """
                        INSERT INTO reviews (user_id, film_id, text, rating,
                                            likes_count, dislikes_count,
                                            created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            new_user_id,
                            new_film_id,
                            f"Тестовый отзыв для realtime теста "
                            f"{uuid.uuid4()}",
                            random.randint(1, 10),
                            random.randint(0, 5),
                            random.randint(0, 2),
                            base_date
                        )
                    )
                conn.commit()
            except psycopg2.IntegrityError:
                conn.rollback()
                # При конфликте генерируем новые ID и пробуем снова
                new_user_id = str(uuid.uuid4())
                new_film_id = str(uuid.uuid4())
                if "bookmarks" in sql.lower():
                    cursor.execute(
                        "INSERT INTO bookmarks (user_id, film_id, created_at) "
                        "VALUES (%s, %s, %s)",
                        (new_user_id, new_film_id, base_date)
                    )
                elif "likes" in sql.lower():
                    cursor.execute(
                        "INSERT INTO likes (user_id, film_id, "
                        "rating, created_at) "
                        "VALUES (%s, %s, %s, %s)",
                        (
                            new_user_id, new_film_id,
                            random.randint(1, 10), base_date
                        )
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO reviews (user_id, film_id, text, rating,
                                            likes_count, dislikes_count,
                                            created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            new_user_id,
                            new_film_id,
                            f"Тестовый отзыв для realtime теста "
                            f"{uuid.uuid4()}",
                            random.randint(1, 10),
                            random.randint(0, 5),
                            random.randint(0, 2),
                            base_date
                        )
                    )
                conn.commit()

            start = time.time()

            # Ждем появления документа в результатах
            timeout = 5.0
            poll_interval = 0.01
            found = False
            rows_after = []

            while (time.time() - start) < timeout:
                # Определяем параметры для запроса
                if "user_id" in param_types:
                    params = (new_user_id,)
                elif "film_id" in param_types:
                    params = (new_film_id,)
                else:
                    params = None
                
                cursor.execute(sql, params)
                rows_after = cursor.fetchall()

                # Проверяем, появился ли новый документ
                if len(rows_after) > 0:
                    for row in rows_after:
                        # Для запросов с film_id проверяем первый элемент
                        if "film_id" in param_types and row[0] == new_film_id:
                            found = True
                            break
                        # Для запросов с user_id проверяем первый элемент
                        elif (
                            "user_id" in param_types
                            and row[0] == new_user_id
                        ):
                            found = True
                            break
                
                if found:
                    break

                time.sleep(poll_interval)

            elapsed = time.time() - start

            result = results[query_idx]
            result.times.append(elapsed)
            result.rows_returned = len(rows_after)
            result.rows_read = len(rows_after)

            status = "OK" if found else "TIMEOUT"
            latency_ms = elapsed * 1000
            sys.stdout.write(
                f"\r  [{name}] Прогон {run + 1}/{config.QUERY_RUNS}... "
                f"latency={latency_ms:.1f}мс [{status}]"
            )
            sys.stdout.flush()
        
        print()
    
    cursor.close()
    conn.close()
    return results


def run_realtime_test(
    test_user_id: Optional[str] = None,
    test_film_id: Optional[str] = None
) -> list[QueryResult]:
    """
    Тест задержки появления данных в реальном времени.

    Args:
        test_user_id: Тестовый user_id (не используется,
            генерируются уникальные ID)
        test_film_id: Тестовый film_id (не используется,
            генерируются уникальные ID)
    """
    print(f"\n{'=' * 60}")
    print("ТЕСТ ЧТЕНИЯ В РЕАЛЬНОМ ВРЕМЕНИ")
    n_queries = len(ANALYTIC_QUERIES)
    print(f"  {n_queries} запросов x {config.QUERY_RUNS} прогонов")
    print(f"{'=' * 60}")

    results = read_realtime()
    
    print("\n  Тест реального времени завершен.")
    return results


# ---------------------------------------------------------------------------
# Concurrent-тест (чтение при активной записи)
# ---------------------------------------------------------------------------
def _continuous_writer_likes(stop_event: threading.Event) -> None:
    """
    Бесконечно вставляет лайки пока stop_event не установлен.
    При конфликте (дублирование user_id, film_id) повторяет
        попытку с новыми данными.
    """
    while not stop_event.is_set():
        conn = create_connection()
        cursor = conn.cursor()
        
        try:
            # Генерируем батч с гарантированно уникальными ID
            batch = generate_likes_batch_unique(
                config.BATCH_SIZE // 3, force_unique=True
            )
            psycopg2.extras.execute_values(
                cursor,
                "INSERT INTO likes (user_id, film_id, rating, created_at) "
                "VALUES %s",
                batch
            )
            conn.commit()
        except psycopg2.IntegrityError:
            # При конфликте просто откатываем и пробуем снова
            conn.rollback()
        except Exception:
            # При других ошибках тоже откатываем
            with contextlib.suppress(Exception):
                conn.rollback()
        finally:
            cursor.close()
            conn.close()


def _continuous_writer_reviews(stop_event: threading.Event) -> None:
    """
    Бесконечно вставляет рецензии пока stop_event не установлен.
    При конфликте повторяет попытку с новыми данными.
    """
    while not stop_event.is_set():
        conn = create_connection()
        cursor = conn.cursor()
        
        try:
            # Генерируем батч с гарантированно уникальными ID
            batch = generate_reviews_batch_unique(
                config.BATCH_SIZE // 3, force_unique=True
            )
            psycopg2.extras.execute_values(
                cursor,
                "INSERT INTO reviews (user_id, film_id, text, rating, "
                "likes_count, dislikes_count, created_at) VALUES %s",
                batch
            )
            conn.commit()
        except psycopg2.IntegrityError:
            # При конфликте просто откатываем и пробуем снова
            conn.rollback()
        except Exception:
            # При других ошибках тоже откатываем
            with contextlib.suppress(Exception):
                conn.rollback()
        finally:
            cursor.close()
            conn.close()


def _continuous_writer_bookmarks(stop_event: threading.Event) -> None:
    """
    Бесконечно вставляет закладки пока stop_event не установлен.
    При конфликте (дублирование user_id, film_id) повторяет
        попытку с новыми данными.
    """
    while not stop_event.is_set():
        conn = create_connection()
        cursor = conn.cursor()
        
        try:
            # Генерируем батч с гарантированно уникальными ID
            batch = generate_bookmarks_batch_unique(
                config.BATCH_SIZE // 3, force_unique=True
            )
            psycopg2.extras.execute_values(
                cursor,
                "INSERT INTO bookmarks (user_id, film_id, created_at) "
                "VALUES %s",
                batch
            )
            conn.commit()
        except psycopg2.IntegrityError:
            # При конфликте просто откатываем и пробуем снова
            conn.rollback()
        except Exception:
            # При других ошибках тоже откатываем
            with contextlib.suppress(Exception):
                conn.rollback()
        finally:
            cursor.close()
            conn.close()


def run_concurrent_read_test(
    test_user_id: Optional[str] = None,
    test_film_id: Optional[str] = None
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
                target=_continuous_writer_likes, args=(stop_event,),
                daemon=True
            )
        elif i % 3 == 1:
            t = threading.Thread(
                target=_continuous_writer_reviews, args=(stop_event,),
                daemon=True
            )
        else:
            t = threading.Thread(
                target=_continuous_writer_bookmarks, args=(stop_event,),
                daemon=True
            )
        t.start()
        writers.append(t)
        print(f"  Старт фонового писателя #{i + 1}")

    # Ждем пока писатели наберут обороты
    time.sleep(2)

    # Выполняем те же запросы, что и в тесте без нагрузки,
    # но при активной записи
    conn = create_connection()
    
    clear_postgres_cache(conn)
    
    results: list[QueryResult] = []

    for name, sql, param_types in ANALYTIC_QUERIES:
        # Определяем параметры для запроса
        params = None
        if "user_id" in param_types:
            params = (test_user_id,)
        elif "film_id" in param_types:
            params = (test_film_id,)
        
        qr = run_single_query(conn, name, sql, config.QUERY_RUNS, params)
        results.append(qr)

    conn.close()

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
    w(
        f"  Целевой хост (ВМ):         {config.POSTGRES_HOST}:"
        f"{config.POSTGRES_PORT}"
    )
    w(f"  База данных:               {config.POSTGRES_DB}")
    total_data_rows = (
        config.LIKES_ROWS + config.REVIEWS_ROWS + config.BOOKMARKS_ROWS
    )
    likes_str = f"Likes: {config.LIKES_ROWS:_}"
    reviews_str = f"Reviews: {config.REVIEWS_ROWS:_}"
    bookmarks_str = f"Bookmarks: {config.BOOKMARKS_ROWS:_}"
    w(f"  Объём данных:              {total_data_rows:_} строк "
      f"({likes_str}, {reviews_str}, {bookmarks_str})")
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
    w(
        f"  {'Запрос':<50} {'Avg':>7} {'Min':>7} {'Max':>7} {'Status':>6}"
    )
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
    header = (
        f"  {'Запрос':<46} {'Avg':>7} {'Min':>7} "
        f"{'Max':>7} {'Deg%':>7} {'Status':>6}"
    )
    w(header)
    w("  " + "-" * 90)
    for i, qr in enumerate(concurrent_results):
        short = qr.name[:44]
        baseline = read_results[i].avg_time if i < len(read_results) else 0
        if baseline > 0:
            degrad = ((qr.avg_time - baseline) / baseline * 100)
        else:
            degrad = 0
        status = "PASS" if qr.avg_time <= threshold else "FAIL"
        w(
            f"  {short:<46} "
            f"{qr.avg_time:>7.4f} {qr.min_time:>7.4f} "
            f"{qr.max_time:>7.4f} {degrad:>6.1f}% {status:>6}"
        )
    w()
    w("  Deg% — процент замедления запроса под нагрузкой.")
    w()

    # === ЧТЕНИЕ В РЕАЛЬНОМ ВРЕМЕНИ (ИНФОРМАЦИЯ) ===
    w("-" * 64)
    w("  РЕЗУЛЬТАТЫ ЧТЕНИЯ В РЕАЛЬНОМ ВРЕМЕНИ (ИНФОРМАЦИЯ)")
    w("-" * 64)
    w(
        f"  {'Запрос':<50} {'latency_ms':>12}"
    )
    w("  " + "-" * 64)
    for qr in realtime_results:
        short = qr.name[:48]
        avg_latency_ms = qr.avg_time * 1000
        w(
            f"  {short:<50} {avg_latency_ms:>12.1f}"
        )
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
        time_ms = qr.avg_time * 1000
        threshold_ms = threshold * 1000
        if qr.avg_time <= threshold:
            status_str = f"PASS ({time_ms:.1f}мс)"
        else:
            status_str = f"FAIL ({time_ms:.1f}мс > {threshold_ms}мс)"
        if qr.avg_time > threshold:
            all_pass_no_load = False
        w(f"    {qr.name:<50} [{status_str}]")
    w()

    # С нагрузкой
    w("  С КОНКУРЕНТНОЙ НАГРУЗКОЙ (порог < 200 мс):")
    all_pass_concurrent = True
    for qr in concurrent_results:
        time_ms = qr.avg_time * 1000
        threshold_ms = threshold * 1000
        if qr.avg_time <= threshold:
            status_str = f"PASS ({time_ms:.1f}мс)"
        else:
            status_str = f"FAIL ({time_ms:.1f}мс > {threshold_ms}мс)"
        if qr.avg_time > threshold:
            all_pass_concurrent = False
        w(f"    {qr.name:<50} [{status_str}]")
    w()

    # === ОБЩИЙ ВЕРДИКТ ===
    w("-" * 64)
    w("  ОБЩИЙ ВЕРДИКТ")
    w("-" * 64)

    all_pass = all_pass_no_load and all_pass_concurrent

    if all_pass:
        w("  [PASS] ВСЕ ЗАПРОСЫ ПРОХОДЯТ (< 200 мс)")
        w("  PostgreSQL удовлетворяет требованию по скорости")
        w("  обработки запросов.")
    elif all_pass_no_load and not all_pass_concurrent:
        w("  [WARN] Без нагрузки все запросы проходят,")
        w(
            f"         но {len(fails_concurrent)} запрос(ов) НЕ проходят "
            "с нагрузкой."
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
            "(< 200 мс)"
        )
        w(
            f"         С нагрузкой:  {len(fails_concurrent)} не проходит "
            "(< 200 мс)"
        )
        w(
            "  Рекомендуется пересмотреть схему или "
            "использовать другое хранилище."
        )
    w()

    if fails_no_load:
        w("  Запросы, не прошедшие тест БЕЗ нагрузки:")
        for qr in fails_no_load:
            w(f"    - {qr.name}: avg={qr.avg_time*1000:.1f}мс")
    if fails_concurrent:
        w("  Запросы, не прошедшие тест С НАГРУЗКОЙ:")
        for qr in fails_concurrent:
            w(f"    - {qr.name}: avg={qr.avg_time*1000:.1f}мс")
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
    print("  PostgreSQL Benchmark")
    print(f"  Хост: {config.POSTGRES_HOST}:{config.POSTGRES_PORT}")
    print(f"  БД:   {config.POSTGRES_DB}")
    print("=" * 60)

    # 1. Setup
    print("\n[1/5] Подготовка базы данных...")
    test_user_id, test_film_id = setup_database_with_test_ids()

    # 2. Тест записи
    write_time, write_speed = run_write_test()

    # 3. Тест чтения без нагрузки
    read_results = run_read_tests(
        label="БЕЗ НАГРУЗКИ",
        test_user_id=test_user_id,
        test_film_id=test_film_id
    )

    # 4. Тест чтения с конкурентной нагрузкой
    concurrent_results = run_concurrent_read_test(
        test_user_id, test_film_id
    )

    # 5. Тест чтения в реальном времени (latency)
    realtime_results = run_realtime_test(
        test_user_id, test_film_id
    )

    # 6. Генерация и сохранение отчёта
    print("\n[6/6] Генерация отчёта...")
    report = generate_report(
        write_time, write_speed,
        read_results, concurrent_results,
        realtime_results
    )

    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(script_dir, "POSTGRES_BENCHMARK_REPORT.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"  Отчёт сохранён: {os.path.abspath(report_path)}")

    # Очистка
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS likes")
    cursor.execute("DROP TABLE IF EXISTS reviews")
    cursor.execute("DROP TABLE IF EXISTS bookmarks")
    conn.commit()
    cursor.close()
    conn.close()
    print("  Временные таблицы удалены.")

    # Вывод вердикта в консоль
    print("\n" + report)


def main() -> None:
    """Точка входа с управлением контейнером."""
    # Поднимаем контейнер
    if not start_docker_container():
        print("\n[ERROR] Не удалось запустить PostgreSQL. Выход.")
        sys.exit(1)

    try:
        run_benchmark()
    finally:
        stop_docker_container()


if __name__ == "__main__":
    main()