# To Be Architecture: Примечания к диаграмме

## Новые компоненты

- **analytics-service** (FastAPI) — приём событий пользователей, публикация в Kafka
- **analytics-etl** (Python) — чтение событий из Kafka, запись в ClickHouse
- **Kafka** (Apache Kafka) — брокер событий
- **ClickHouse** (ClickHouse) — аналитическое хранилище событий

## Библиотеки

- **aiokafka** — используется в обоих сервисах (producer в analytics-service, consumer в analytics-etl). Нативно async, совместима с FastAPI и asyncio-скриптами.
- **clickhouse-connect** — официальный async-клиент ClickHouse, используется в analytics-etl.

## Kafka: топики и партиции

**Топик:** `user-activity`

**Producers** (пишут в Kafka):
- `analytics-service` — получает событие от пользователя и публикует в топик `user-activity`

**Consumers** (читают из Kafka):
- `analytics-etl` — подписывается на топик `user-activity`, читает события и пишет в ClickHouse

**Partition key:** `user_id` — события одного пользователя попадают в одну партицию, порядок гарантирован.

**Партиции:** 3 (разработка) / 6 (production).

**Гарантия доставки:**
- **client → analytics-service:** at-most-once — сервис принимает событие в in-memory буфер и немедленно отвечает 202; при краше сервиса события в буфере теряются (для аналитики допустимо)
- **Kafka → ClickHouse:** at-most-once — ETL коммитит offset до вставки в ClickHouse; при сбое вставки события могут теряться (для аналитики допустимо; исключает накопление дубликатов в MergeTree)

**Буферизация (analytics-service → Kafka):**

Между приёмом события и отправкой в Kafka находится асинхронный in-memory буфер (`asyncio.Queue`):
- Размер настраивается через `KAFKA_BUFFER_SIZE` (по умолчанию 10 000 сообщений)
- При пиковом RPS ~15 событий/сек буфер рассчитан на ~11 минут — достаточно для перезапуска брокера
- При переполнении буфера сервис возвращает 503 Service Unavailable
- Факт потери события в Kafka логируется

**Конфигурация:**
- Брокеров: 3 — при падении 1 брокера кворум сохраняется
- Replication factor: 3 — каждая партиция хранится на 3 брокерах
- min.insync.replicas: 2 — запись подтверждается при наличии минимум 2 актуальных реплик

## Структура события в Kafka

Клиент отправляет в analytics-service:

```json
POST /api/v1/analytics/events/
{
  "event_type": "film_view",
  "object_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "payload": {},
  "event_time": "2026-07-11T10:30:00Z"
}
```

analytics-service добавляет `user_id` из JWT, публикует в топик:

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "film_view",
  "object_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "payload": {},
  "event_time": "2026-07-11T10:30:00Z"
}
```

`event_time` — время события на стороне клиента.

`object_id` — идентификатор объекта события: `film_id`, `genre_id` или `person_id` в зависимости от `event_type`.

`payload` — опциональный контекст:
- `search_filter_used`: `{"genre": "action", "sort": "rating"}`
- `video_quality_changed`: `{"from": "720p", "to": "1080p"}`
- `film_view`, `genre_view`, `person_view`: `{}`

## Типы событий (event_type)

Есть соответствующий эндпоинт в movies-service:
- `film_view` — `GET /api/v1/films/{id}`
- `films_list_view` — `GET /api/v1/films/`
- `film_search` — `GET /api/v1/films/search/`
- `genre_view` — `GET /api/v1/genres/{id}`
- `person_view` — `GET /api/v1/persons/{id}`
- `person_films_view` — `GET /api/v1/persons/{id}/film/`
- `search_filter_used` — query-параметры на `/films/` и `/films/search/`

Только браузерное событие (нет backend-эндпоинта):
- `trailer_click` — клик по трейлеру
- `page_time_spent` — время на странице

Требует сервиса видеостриминга:
- `video_quality_changed` — смена качества видео
- `video_completed` — просмотр до конца

## Фронтенд

В текущей реализации фронтенд отсутствует. Событие инициируется вручную через API-клиент (curl, Postman):

1. Получить `access_token` через `POST /api/v1/login`
2. Отправить событие: `POST /api/v1/analytics/events/` с заголовком `Authorization: Bearer <token>`
3. Проверить запись в ClickHouse

## Изменения в существующих компонентах

- **nginx** — добавлен маршрут `/api/v1/analytics/**` → `analytics-service`
- **analytics-service** — отправляет OTLP-трейсы в otel-collector
