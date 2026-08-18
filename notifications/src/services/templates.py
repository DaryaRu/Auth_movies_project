"""Сервис для операций над шаблонами."""

from typing import Any
from uuid import UUID

from src.render import render
from src.repositories.templates import TemplateRepository
from src.schemas.templates import TemplatePreviewResponse
from src.services.notifications import (
    InvalidPayloadError,
    TemplateNotFoundError,
)


class TemplateService:
    """Сервис для шаблонов."""

    def __init__(self, template_repository: TemplateRepository):
        self.template_repo = template_repository

    async def preview(
        self, template_id: UUID, payload: dict[str, Any]
    ) -> TemplatePreviewResponse:
        """Отрендерить шаблон с тестовым payload тем же движком, что и
        воркер при реальной отправке (notifications/worker/render.py).
        """
        template = await self.template_repo.get_by_id(template_id)
        if template is None:
            raise TemplateNotFoundError(str(template_id))

        if template.allowed_variables:
            unknown_keys = set(payload.keys()) - set(
                template.allowed_variables
            )
            if unknown_keys:
                raise InvalidPayloadError(unknown_keys)

        rendered_body = render(template.body, payload)
        assert rendered_body is not None

        return TemplatePreviewResponse(
            subject=render(template.subject, payload),
            body=rendered_body,
        )
