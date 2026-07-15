"""
Benchmark-скрипт для тестирования производительности Vertica.

Поддерживаемые режимы:
  1. Тест записи без нагрузки (INSERT)
  2. Тест чтения без нагрузки (SELECT Q1-Q5)
  3. Тест чтения с конкурентной нагрузкой (SELECT при активных INSERT)

Конфигурация берётся из файла .env в той же директории.

Использование:
    python benchmark_vertica.py
"""

import contextlib
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

import vertica_python
from dotenv import load_dotenv

vertica_python.VerticaConnection = vertica_python.Connection

# ----- PATHS -----
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(_SCRIPT_DIR, ".env")
DOCKER_COMPOSE_FILE = os.path.join(_SCRIPT_DIR, "docker-compose.benchmark.yml")
DATA_DIR = os.path.join(_SCRIPT_DIR, "data", "vertica_data")
load_dotenv(ENV_PATH)


def wait_for_vertica_ready() -> bool:
    """
    Ожидает готовности Vertica к подключениям.
    Возвращает True если база готова, False если таймаут.
    """
    print("Ожидание готовности Vertica...")

    conn_info = {
        "host": os.environ.get("VERTICA_HOST", "127.0.0.1"),
        "port": os.environ.get("VERTICA_PORT", "5434"),
        "user": os.environ.get("VERTICA_USER", "dbadmin"),
        "password": os.environ.get("VERTICA_PASSWORD", "password"),
        "database": os.environ.get("VERTICA_DATABASE", "analytics"),
        "connection_load_balance": False,
        "tlsmode": 'disable',
        "use_load_balancing": False,
    }

    ready = False
    # Делаем 30 попыток с интервалом в 10 секунд (всего 5 минут)
    for i in range(30):
        try:
            conn = vertica_python.connect(**conn_info)
            conn.close()
            ready = True
            print("  Vertica полностью готова к работе!")
            break
        except Exception as e:
            # Если база еще создается или рестартует, пишем точку и ждем
            print(".", end="", flush=True)
            time.sleep(10)

    if not ready:
        print("\n  Ошибка: Vertica не успела запуститься за отведенное время.")
        return False

    return True


def start_docker_container() -> bool:
    """Запускает контейнер через docker compose. Использует локальный образ если есть."""
    print("\n[START] Поднимаем контейнер Vertica...")

    # Проверяем, есть ли локальный образ
    try:
        result = subprocess.run(
            ["docker", "images", "-q", "jbfavre/vertica:latest"],
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout.strip():
            print("  Локальный образ jbfavre/vertica:latest найден - используем его")
        else:
            print("  Локальный образ не найден - docker compose скачает его автоматически")
    except subprocess.CalledProcessError:
        print("  Не удалось проверить наличие локального образа")

    # Запускаем контейнер
    subprocess.run(
        ["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "up", "-d"],
        check=True,
        cwd=_SCRIPT_DIR
    )
    print("  Контейнер запущен")

    # Ждем готовности Vertica
    return wait_for_vertica_ready()


def stop_docker_container() -> None:
    """Останавливает и удаляет контейнер через docker compose."""
    print("\n[STOP] Останавливаем контейнер Vertica...")
    subprocess.run(
        ["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "down"],
        cwd=_SCRIPT_DIR,
        check=True
    )
    print("  Контейнер остановлен")


@dataclass
class Config:
    """Централизованная конфигурация BenchMark-скрипта."""
    VERTICA_HOST: str = os.environ.get("VERTICA_HOST", "localhost")
    VERTICA_PORT: int = int(os.environ.get("VERTICA_PORT", "5434"))
    VERTICA_USER: str = os.environ.get("VERTICA_USER", "dbadmin")
    VERTICA_PASSWORD: str = os.environ.get("VERTICA_PASSWORD", "password")
    VERTICA_DATABASE: str = os.environ.get("VERTICA_DATABASE", "analytics")

    TOTAL_ROWS: int = int(os.environ.get("TOTAL_ROWS", "10000000"))
    BATCH_SIZE: int = int(os.environ.get("BATCH_SIZE", "1000"))
    THREADS: int = int(os.environ.get("THREADS", "4"))

    QUERY_RUNS: int = int(os.environ.get("QUERY_RUNS", "5"))

    CONCURRENT_WRITER_THREADS: int = int(
        os.environ.get("CONCURRENT_WRITER_THREADS", "4")
    )
    CONCURRENT_WRITE_DURATION_SEC: int = int(
        os.environ.get("CONCURRENT_WRITE_DURATION_SEC", "120")
    )


config = Config()

# ---------------------------------------------------------------------------
# Константы генерации данных
# ---------------------------------------------------------------------------
EVENT_TYPES = [
    "film_view",
    "films_list_view",
    "film_search",
    "genre_view",
    "person_view",
    "trailer_click",
    "page_time_spent",
    "video_quality_changed",
    "video_completed",
]

GENRES = ["action", "comedy", "drama", "horror", "scifi", "romance", "documentary"]
QUALITIES = ["360p", "480p", "720p", "1080p", "4K"]
SORT_OPTIONS = ["rating", "year", "popularity", "name"]


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

    @property
    def median_time(self) -> float:
        return statistics.median(self.times) if self.times else 0.0

    @property
    def rows_per_sec(self) -> float:
        return self.rows_read / self.avg_time if self.avg_time > 0 else 0.0

    @property
    def mb_per_sec(self) -> float:
        return (self.bytes_read / (1024 * 1024)) / self.avg_time if self.avg_time > 0 else 0.0


# ---------------------------------------------------------------------------
# Генерация данных
# ---------------------------------------------------------------------------
def generate_batch(size: int) -> list[tuple]:
    """Генерация пачки данных для вставки."""
    batch: list[tuple] = []
    base_date = datetime.now()
    for _ in range(size):
        event_type = random.choice(EVENT_TYPES)
        user_id = str(uuid.uuid4())
        object_id = (
            None
            if event_type in ("film_search", "films_list_view")
            else str(uuid.uuid4())
        )

        if event_type == "film_search":
            payload = {
                "genre": random.choice(GENRES),
                "sort": random.choice(SORT_OPTIONS),
            }
        elif event_type == "video_quality_changed":
            payload = {
                "from": random.choice(QUALITIES),
                "to": random.choice(QUALITIES),
            }
        elif event_type == "page_time_spent":
            payload = {"seconds": random.randint(5, 600)}
        elif event_type == "film_view":
            payload = {"watched_seconds": random.randint(10, 3600)}
        elif event_type == "video_completed":
            payload = {"duration": random.randint(1800, 7200)}
        else:
            payload = {}

        event_time = base_date - timedelta(seconds=random.randint(0, 2592000))
        batch.append(
            (user_id, event_type, object_id, json.dumps(payload), event_time)
        )
    return batch


# ---------------------------------------------------------------------------
# Подключение к Vertica
# ---------------------------------------------------------------------------
def create_client() -> vertica_python.VerticaConnection:
    """Создаёт клиент Vertica."""
    conn_info = {
        "host": config.VERTICA_HOST,
        "port": config.VERTICA_PORT,
        "user": config.VERTICA_USER,
        "password": config.VERTICA_PASSWORD,
        "database": config.VERTICA_DATABASE,
        "connection_load_balance": True,
        "tlsmode": 'disable',
        "use_load_balancing": False, 
    }
    return vertica_python.connect(**conn_info)


# ---------------------------------------------------------------------------
# Подготовка/schema
# ---------------------------------------------------------------------------
def setup_database(conn: vertica_python.VerticaConnection) -> None:
    """Создаёт БД и таблицу для тестов."""
    cursor = conn.cursor()

    cursor.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    # Создаем таблицу
    cursor.execute("DROP TABLE IF EXISTS analytics.events")

    cursor.execute(
        '''
        CREATE TABLE analytics.events (
            user_id UUID,
            event_type VARCHAR(255),
            object_id UUID,
            payload VARCHAR(65000),
            event_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
        ORDER BY event_type, event_time, user_id
        SEGMENTED BY HASH(user_id) ALL NODES
        '''
    )
    print("  Таблица analytics.events создана.")
    conn.commit()
    cursor.close()


# ---------------------------------------------------------------------------
# Запись данных
# ---------------------------------------------------------------------------
def writer_worker() -> None:
    """Одна итерация записи одной пачки в отдельном потоке."""
    conn = create_client()
    cursor = conn.cursor()
    batch_data = generate_batch(config.BATCH_SIZE)

    cursor.executemany(
        "INSERT INTO analytics.events (user_id, event_type, object_id, payload, event_time) VALUES (%s, %s, %s, %s, %s)",
        batch_data
    )
    conn.commit()
    cursor.close()
    conn.close()


def run_write_test() -> tuple[float, float]:
    """
    Тест записи без нагрузки.
    Возвращает (total_time_sec, rows_per_sec).
    """
    print(f"\n{'=' * 60}")
    print("ТЕСТ ЗАПИСИ БЕЗ НАГРУЗКИ")
    print(f"  {config.TOTAL_ROWS:_} строк, {config.BATCH_SIZE}/пачка, "
          f"{config.THREADS} потоков")
    print(f"{'=' * 60}")

    total_batches = config.TOTAL_ROWS // config.BATCH_SIZE
    start = time.time()

    with ThreadPoolExecutor(max_workers=config.THREADS) as executor:
        futures = [executor.submit(writer_worker) for _ in range(total_batches)]
        for f in futures:
            f.result()

    elapsed = time.time() - start
    speed = config.TOTAL_ROWS / elapsed
    print(f"  Запись завершена за {elapsed:.2f} сек.")
    print(f"  Скорость: {speed:,.2f} строк/сек")
    return elapsed, speed


# ---------------------------------------------------------------------------
# SQL-запросы для тестов (Vertica)
# ---------------------------------------------------------------------------
ANALYTIC_QUERIES: list[tuple[str, str]] = [
    (
        "Q1: Агрегация с JSON (genre distribution)",
        '''
         SELECT
             MAPLOOKUP(MapJSONExtractor(payload), 'genre')::VARCHAR AS genre,
             COUNT(*) AS cnt
         FROM analytics.events
         WHERE event_type = 'film_search'
           AND MAPLOOKUP(MapJSONExtractor(payload), 'genre')::VARCHAR LIKE '%action%'
         GROUP BY genre
         ORDER BY cnt DESC
         ''',
     ),
     (
         "Q2: Фильтрация по временному окну",
         '''
         SELECT
             event_type,
             COUNT(*) AS cnt
         FROM analytics.events
         WHERE event_time >= GETDATE() - INTERVAL '30 DAY'
         GROUP BY event_type
         ORDER BY cnt DESC
         ''',
     ),
     (
         "Q3: Оконная функция — ранжирование пользователей",
         '''
         SELECT user_id, view_count, rn FROM (
             SELECT
                 user_id,
                 view_count,
                 ROW_NUMBER() OVER (ORDER BY view_count DESC) AS rn
             FROM (
                 SELECT user_id, COUNT(*) AS view_count
                 FROM analytics.events
                 WHERE event_type = 'film_view'
                 GROUP BY user_id
             ) grp
         ) t WHERE rn <= 100
         ORDER BY view_count DESC
         ''',
     ),
     (
         "Q4: Сложная агрегация по дате и типу события",
         '''
         SELECT
             event_time::DATE AS day,
             event_type,
             COUNT(*) AS events,
             COUNT(DISTINCT user_id) AS unique_users
         FROM analytics.events
         WHERE event_time >= GETDATE() - INTERVAL '90 DAY'
         GROUP BY event_time::DATE, event_type
         ORDER BY day DESC, events DESC
         LIMIT 1000
         ''',
     ),
     (
         "Q5: Подзапрос — топ-активные пользователи с деталями",
         '''
         SELECT
             me.user_id,
             me.event_type,
             me.event_time,
             me.payload
         FROM analytics.events me
         INNER JOIN (
             SELECT user_id FROM (
                 SELECT user_id, COUNT(*) AS cnt,
                        ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) as rank
                 FROM analytics.events
                 GROUP BY user_id
                 HAVING COUNT(*) > 10
             ) rnk_t WHERE rank <= 50
         ) top ON me.user_id = top.user_id
         ORDER BY me.event_time DESC
         LIMIT 5000
         ''',
     ),
]



# ---------------------------------------------------------------------------
# Выполнение запросов
# ---------------------------------------------------------------------------
def run_single_query(
    conn: vertica_python.VerticaConnection,
    name: str,
    sql: str,
    runs: int,
) -> QueryResult:
    """
    Выполняет один запрос N раз, собирает статистику.
    Возвращает QueryResult.
    """
    result = QueryResult(name=name)
    cursor = conn.cursor()

    for i in range(runs):
        start = time.time()
        cursor.execute(sql)
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


def run_read_tests(label: str = "БЕЗ НАГРУЗКИ") -> list[QueryResult]:
    """
    Запускает все аналитические запросы и возвращает результаты.
    """
    print(f"\n{'=' * 60}")
    print(f"  ТЕСТ ЧТЕНИЯ {label}")
    print(f"  {len(ANALYTIC_QUERIES)} запросов x {config.QUERY_RUNS} прогонов")
    print(f"{'=' * 60}")

    conn = create_client()
    results: list[QueryResult] = []

    for name, sql in ANALYTIC_QUERIES:
        qr = run_single_query(conn, name, sql, config.QUERY_RUNS)
        results.append(qr)

    conn.close()
    return results


# ---------------------------------------------------------------------------
# Concurrent-тест (чтение при активной записи)
# ---------------------------------------------------------------------------
def _continuous_writer(stop_event: threading.Event) -> None:
    """Бесконечно вставляет данные пока stop_event не установлен."""
    while not stop_event.is_set():
        with contextlib.suppress(Exception):
            writer_worker()


def run_concurrent_tests() -> list[QueryResult]:
    """
    Запускает аналитические запросы при активной фоновой записи.
    """
    print(f"\n{'=' * 60}")
    print("ТЕСТ ЧТЕНИЯ С КОНКУРЕНТНОЙ НАГРУЗКОЙ")
    print(f"  {config.CONCURRENT_WRITER_THREADS} фоновых писателей, "
          f"длительность ~{config.CONCURRENT_WRITE_DURATION_SEC}с")
    print(f"{'=' * 60}")

    stop_event = threading.Event()
    writers: list[threading.Thread] = []

    for i in range(config.CONCURRENT_WRITER_THREADS):
        t = threading.Thread(target=_continuous_writer, args=(stop_event,), daemon=True)
        t.start()
        writers.append(t)
        print(f"  Старт писателя #{i + 1}")

    time.sleep(2)

    results = run_read_tests(label="С КОНКУРЕНТНОЙ НАГРУЗКОЙ")

    print("  Остановка писателей...")
    stop_event.set()
    for t in writers:
        t.join(timeout=5)

    return results


# ---------------------------------------------------------------------------
# Формирование отчёта
# ---------------------------------------------------------------------------
def generate_report(
    write_time: float,
    write_speed: float,
    read_results: list[QueryResult],
    concurrent_results: list[QueryResult],
) -> str:
    """Генерирует текстовый отчёт и возвращает его."""
    threshold = 10.0  # секунды — требование производительности
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
    w(f"  Целевой хост (ВМ):         {config.VERTICA_HOST}:{config.VERTICA_PORT}")
    w(f"  База данных:               {config.VERTICA_DATABASE}")
    w(f"  Объём данных:              {config.TOTAL_ROWS:_} строк")
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
        f"  {'Запрос':<50} {'Avg':>7} {'Min':>7} {'Max':>7} "
        f"{'rows/s':>12} {'MB/s':>10} {'Status':>6}"
    )
    w("  " + "-" * 105)
    for qr in read_results:
        short = qr.name[:48]
        status = "PASS" if qr.avg_time <= threshold else "FAIL"
        w(
            f"  {short:<50} "
            f"{qr.avg_time:>7.4f} {qr.min_time:>7.4f} {qr.max_time:>7.4f} "
            f"{qr.rows_per_sec:>12,.0f} {qr.mb_per_sec:>10.2f} "
            f"{status:>6}"
        )
    w()

    # === ЧТЕНИЕ С НАГРУЗКОЙ ===
    w("-" * 64)
    w("  РЕЗУЛЬТАТЫ ЧТЕНИЯ С КОНКУРЕНТНОЙ НАГРУЗКОЙ")
    w("-" * 64)
    w(
        f"  {'Запрос':<46} {'Avg':>7} {'Min':>7} {'Max':>7} "
        f"{'rows/s':>12} {'MB/s':>10} {'Deg%':>7} {'Status':>6}"
    )
    w("  " + "-" * 115)
    for i, qr in enumerate(concurrent_results):
        short = qr.name[:44]
        baseline = read_results[i].avg_time if i < len(read_results) else 0
        degrad = ((qr.avg_time - baseline) / baseline * 100) if baseline > 0 else 0
        status = "PASS" if qr.avg_time <= threshold else "FAIL"
        w(
            f"  {short:<46} "
            f"{qr.avg_time:>7.4f} {qr.min_time:>7.4f} {qr.max_time:>7.4f} "
            f"{qr.rows_per_sec:>12,.0f} {qr.mb_per_sec:>10.2f} "
            f"{degrad:>6.1f}% {status:>6}"
        )
    w()
    w("  Deg% — процент замедления запроса под нагрузкой.")
    w()

    # === ПРОВЕРКА ТРЕБОВАНИЯ < 10 СЕК ===
    w("=" * 64)
    w("  ПРОВЕРКА ТРЕБОВАНИЯ: обработка агрегирующего запроса < 10 секунд")
    w("=" * 64)
    w()

    fails_no_load = [qr for qr in read_results if qr.avg_time > threshold]
    fails_concurrent = [qr for qr in concurrent_results if qr.avg_time > threshold]

    # Без нагрузки
    w("  БЕЗ НАГРУЗКИ:")
    all_pass_no_load = True
    for qr in read_results:
        status_str = f"PASS ({qr.avg_time:.2f}с)" if qr.avg_time <= threshold else f"FAIL ({qr.avg_time:.2f}с > {threshold}с)"
        if qr.avg_time > threshold:
            all_pass_no_load = False
        w(f"    {qr.name:<50} [{status_str}]")
    w()

    # С нагрузкой
    w("  С КОНКУРЕНТНОЙ НАГРУЗКОЙ:")
    all_pass_concurrent = True
    for qr in concurrent_results:
        status_str = f"PASS ({qr.avg_time:.2f}с)" if qr.avg_time <= threshold else f"FAIL ({qr.avg_time:.2f}с > {threshold}с)"
        if qr.avg_time > threshold:
            all_pass_concurrent = False
        w(f"    {qr.name:<50} [{status_str}]")
    w()

    # === ОБЩИЙ ВЕРДИКТ ===
    w("-" * 64)
    w("  ОБЩИЙ ВЕРДИКТ")
    w("-" * 64)

    if all_pass_no_load and all_pass_concurrent:
        w("  [PASS] ВСЕ ЗАПРОСЫ ПРОХОДЯТ (< 10с)")
        w("  Vertica удовлетворяет требованию по скорости")
        w("  обработки агрегирующих запросов.")
    elif all_pass_no_load and not all_pass_concurrent:
        w("  [WARN] Без нагрузки все запросы проходят,")
        w(f"         но {len(fails_concurrent)} запрос(ов) НЕ проходят с нагрузкой.")
        w("  Рекомендуется оптимизировать индексы или увеличить ресурсы.")
    elif not all_pass_no_load and all_pass_concurrent:
        w("  [WARN] Без нагрузки НЕ проходят запросы,")
        w("         но с нагрузкой все проходят (возможно, кэширование).")
        w("  Рекомендуется повторить тест без кэша.")
    else:
        w("  [FAIL] ТРЕБОВАНИЕ НЕ ВЫПОЛНЕНО.")
        w(f"         Без нагрузки: {len(fails_no_load)} не проходит")
        w(f"         С нагрузкой:  {len(fails_concurrent)} не проходит")
        w("  Рекомендуется пересмотреть схему или использовать другое хранилище.")
    w()

    if fails_no_load:
        w("  Запросы, не прошедшие тест БЕЗ нагрузки:")
        for qr in fails_no_load:
            w(f"    - {qr.name}: avg={qr.avg_time:.2f}с")
    if fails_concurrent:
        w("  Запросы, не прошедшие тест С НАГРУЗКОЙ:")
        for qr in fails_concurrent:
            w(f"    - {qr.name}: avg={qr.avg_time:.2f}с")
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
    print("  Vertica Benchmark")
    print(f"  Хост: {config.VERTICA_HOST}:{config.VERTICA_PORT}")
    print(f"  БД:   {config.VERTICA_DATABASE}")
    print("=" * 60)

    # 1. Setup
    print("\n[1/4] Подготовка базы данных...")
    main_conn = create_client()
    setup_database(main_conn)
    main_conn.close()

    # 2. Тест записи
    write_time, write_speed = run_write_test()

    # 3. Тест чтения без нагрузки
    read_results = run_read_tests(label="БЕЗ НАГРУЗКИ")

    # 4. Тест чтения с конкурентной нагрузкой
    concurrent_results = run_concurrent_tests()

    # 5. Генерация и сохранение отчёта
    print("\n[5/5] Генерация отчёта...")
    report = generate_report(write_time, write_speed, read_results, concurrent_results)

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERTICA_BENCHMARK_REPORT.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"  Отчёт сохранён: {os.path.abspath(report_path)}")

    # Очистка
    conn = create_client()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS analytics.events")
    conn.commit()
    cursor.close()
    conn.close()
    print("  Временная таблица analytics.events удалена.")

    # Вывод вердикта в консоль
    print("\n" + report)


def main() -> None:
    """Точка входа с управлением контейнером."""
    # Поднимаем контейнер
    if not start_docker_container():
        print("\n[ERROR] Не удалось запустить Vertica. Выход.")
        sys.exit(1)

    try:
        run_benchmark()
    finally:
        stop_docker_container()


if __name__ == "__main__":
    main()
