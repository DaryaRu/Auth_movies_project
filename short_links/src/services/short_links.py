"""Сервис для работы с короткими ссылками."""

import logging
import secrets
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx

from src.core.config import settings
from src.db.http_client import HTTPClient
from src.repositories.short_links import ShortLinkRepository
from src.schemas.short_links import ShortLinkResponse

logger = logging.getLogger(__name__)

# Алфавит для генерации короткого ключа (base62)
_SHORT_KEY_ALPHABET = string.ascii_letters + string.digits
_SHORT_KEY_LENGTH = 8


def _generate_short_key() -> str:
    """Сгенерировать уникальный короткий ключ."""
    return "".join(secrets.choice(_SHORT_KEY_ALPHABET) for _ in range(_SHORT_KEY_LENGTH))


class ShortLinkService:
    """Сервис для управления короткими ссылками."""

    def __init__(self, repository: ShortLinkRepository | None = None):
        self._repository = repository or ShortLinkRepository()

    async def create_short_link(
        self,
        user_id: UUID,
        expires_at: datetime,
        redirect_url: str | None = None,
    ) -> ShortLinkResponse:
        """Создать короткую ссылку.

        Args:
            user_id: ID пользователя.
            expires_at: Срок действия ссылки (datetime, UTC).
            redirect_url: URL для редиректа после подтверждения.

        Returns:
            ShortLinkResponse с данными созданной ссылки.

        Raises:
            ValueError: если expires_at в прошлом или превышает MAX_LINK_TTL_HOURS.
        """
        now = datetime.now(timezone.utc)
        if expires_at <= now:
            raise ValueError("expires_at должен быть в будущем")
        max_allowed = now + timedelta(hours=settings.MAX_LINK_TTL_HOURS)
        if expires_at > max_allowed:
            raise ValueError(
                f"Срок действия не может превышать {settings.MAX_LINK_TTL_HOURS} часов"
            )

        # Генерируем ключ, проверяем уникальность
        for _ in range(10):
            short_key = _generate_short_key()
            link = await self._repository.get_by_short_key(short_key)
            if link is None:
                break
        else:
            raise RuntimeError("Не удалось сгенерировать уникальный ключ")

        await self._repository.create(
            short_key=short_key,
            user_id=user_id,
            expires_at=expires_at,
            redirect_url=redirect_url,
        )

        full_link = f"{settings.SHORT_LINK_BASE_URL}/{short_key}"

        logger.info(
            "Создана короткая ссылка: short_key=%s, user_id=%s, expires_at=%s",
            short_key,
            user_id,
            expires_at,
        )

        return ShortLinkResponse(
            short_key=short_key,
            short_link=full_link,
            expires_at=expires_at,
        )

    async def _confirm_email(self, user_id: UUID) -> None:
        """Подтвердить email пользователя через auth-сервис.

        Args:
            user_id: Идентификатор пользователя.

        Raises:
            httpx.HTTPError: Если запрос к auth-сервису не удался.
        """
        try:
            assert HTTPClient.client is not None
            response = await HTTPClient.client.post(
                f"{settings.AUTH_API_URL}/confirm-email/",
                json={"user_id": str(user_id)},
                headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
                timeout=10,
            )
            response.raise_for_status()
            logger.info(
                "Email подтверждён для пользователя: user_id=%s",
                user_id,
            )
        except httpx.HTTPError as e:
            logger.error(
                "Не удалось подтвердить email для user_id=%s: %s",
                user_id,
                e,
            )
            raise

    async def resolve_short_link(self, short_key: str) -> tuple[UUID, str]:
        """Найти и атомарно подтвердить короткую ссылку.

        Атомарный UPDATE ... WHERE NOT is_used AND expires_at > NOW()
        исключает повторное использование и race condition при параллельных кликах.

        Returns:
            Кортеж (user_id, redirect_url) если ссылка валидна.

        Raises:
            ValueError: если ссылка не найдена, просрочена или уже использована.
        """
        result = await self._repository.consume_short_link(short_key)

        if result is None:
            reason = await self._repository.get_invalid_reason(short_key)
            if reason == "not_found":
                logger.warning("Короткая ссылка не найдена: short_key=%s", short_key)
                raise ValueError("Ссылка не найдена")
            elif reason == "already_used":
                logger.info("Ссылка уже использована: short_key=%s", short_key)
                raise ValueError("Ссылка уже использована")
            else:
                logger.warning("Просроченная короткая ссылка: short_key=%s", short_key)
                raise ValueError("Ссылка просрочена")

        user_id, redirect_url = result

        # Подтверждаем email через auth-сервис
        await self._confirm_email(user_id)

        logger.info(
            "Ссылка успешно активирована: short_key=%s, user_id=%s",
            short_key,
            user_id,
        )

        return user_id, redirect_url
