"""Функциональные тесты эндпоинтов analytics."""

import asyncio
from http import HTTPStatus
from typing import Any
from uuid import uuid4

import pytest
from aiohttp import ClientSession

from analytics.tests.functional.utils.check_methods import (
    assert_status_return_json,
)
from analytics.tests.settings import test_settings

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestEvents:
    """Тесты эндпоинта создания событий analytics."""

    URL = f"{test_settings.api_prefix}/analytics/events/"

    @pytest.mark.parametrize(
        "event_data",
        [
            {"event_type": "film_view", "payload": {}},
            {"event_type": "films_list_view", "payload": {}},
            {"event_type": "genre_view", "payload": {}},
            {"event_type": "person_view", "payload": {}},
            {"event_type": "person_films_view", "payload": {}},
            {"event_type": "trailer_click", "payload": {}},
            {"event_type": "film_start", "payload": {}},
            {"event_type": "video_completed", "payload": {}},
            {"event_type": "film_search", "payload": {"query": "Inception"}},
            {
                "event_type": "page_time_spent",
                "payload": {"page": "main", "seconds": 45},
            },
            {
                "event_type": "film_progress",
                "payload": {"viewed_frame": 1200, "movie_duration": 7200},
            },
            {
                "event_type": "video_quality_changed",
                "payload": {"old_quality": "720p", "new_quality": "1080p"},
            },
            {
                "event_type": "search_filter_used",
                "payload": {"genre": str(uuid4()), "sort": "imdb_rating"},
            },
            {
                "event_type": "player_action",
                "payload": {"action": "play", "position_sec": 10},
            },
        ],
    )
    async def test_create_event_success(
        self,
        http_client: ClientSession,
        event_data: dict[str, Any],
        generate_test_token: str,
    ):
        """Позитивный тест создания всех типов событий analytics."""
        payload = {
            "object_id": str(uuid4()),
            "event_time": "2024-01-01T12:00:00Z",
            **event_data,
        }

        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.ACCEPTED)
        assert data is None

    async def test_create_event_unauthorized(self, http_client: ClientSession):
        """Тест защиты эндпоинта: отсутствие токена авторизации."""
        payload = {
            "event_type": "film_view",
            "event_time": "2024-01-01T12:00:00Z",
            "object_id": str(uuid4()),
        }

        response = await http_client.post(self.URL, json=payload)
        assert response.status == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize(
        "invalid_payload, expected_status",
        [
            (
                {"event_type": "film_view", "object_id": str(uuid4())},
                HTTPStatus.UNPROCESSABLE_ENTITY,
            ),
            (
                {
                    "event_type": "film_view",
                    "event_time": "not-a-date",
                    "object_id": str(uuid4()),
                },
                HTTPStatus.UNPROCESSABLE_ENTITY,
            ),
            ({}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ],
    )
    async def test_create_event_validation_errors(
        self,
        http_client: ClientSession,
        invalid_payload: dict[str, Any],
        expected_status: int,
        generate_test_token: str,
    ):
        """Тест валидации Pydantic-схем входящего события."""
        response = await http_client.post(
            self.URL,
            json=invalid_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        assert response.status == expected_status

    @pytest.mark.parametrize(
        "valid_time",
        [
            "2024-01-01T12:00:00.123456Z",
            "2024-01-01T15:00:00+03:00",
            "2024-01-01 12:00:00Z",
            "2024-01-01",
        ],
    )
    async def test_create_event_valid_time_formats(
        self,
        http_client: ClientSession,
        valid_time: str,
        generate_test_token: str,
    ):
        """Позитивный тест поддержки различных ISO 8601 форматов времени."""
        payload = {
            "event_type": "film_view",
            "object_id": str(uuid4()),
            "event_time": valid_time,
            "payload": {},
        }
        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.ACCEPTED)
        assert data is None

    @pytest.mark.parametrize(
        "invalid_time",
        [
            "2024-02-30T12:00:00Z",
            "2024-01-01T25:00:00Z",
            "12:00:00",
            "not-a-date",
        ],
    )
    async def test_create_event_invalid_time_formats(
        self,
        http_client: ClientSession,
        invalid_time: str,
        generate_test_token: str,
    ):
        """Негативный тест валидации некорректных форматов времени."""
        payload = {
            "event_type": "film_view",
            "object_id": str(uuid4()),
            "event_time": invalid_time,
            "payload": {},
        }
        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_create_event_buffer_full(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Тест поведения системы при переполнении буфера Kafka."""
        payload = {
            "event_type": "film_view",
            "event_time": "2024-01-01T12:00:00Z",
            "object_id": str(uuid4()),
        }

        tasks = [
            http_client.post(
                self.URL,
                json=payload,
                headers={"Authorization": f"Bearer {generate_test_token}"},
            )
            for _ in range(test_settings.kafka_buffer_size + 20)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        statuses = [
            resp.status for resp in responses if hasattr(resp, "status")
        ]

        assert 503 in statuses
