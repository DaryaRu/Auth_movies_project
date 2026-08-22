"""API endpoints для ручных рассылок из админки (admin_mailings)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.repositories.admin_mailings import AdminMailingRepository
from src.repositories.templates import TemplateRepository
from src.schemas.admin_mailings import AdminMailing, AdminMailingCreate
from src.services.admin_mailings import (
    AdminMailingService,
    InvalidScheduledAtError,
)
from src.services.notifications import (
    InvalidPayloadError,
    TemplateNotFoundError,
)

router = APIRouter(prefix="/admin-mailings", tags=["admin-mailings"])


def get_admin_mailing_repository() -> AdminMailingRepository:
    """Получить репозиторий рассылок."""
    return AdminMailingRepository()


AdminMailingRepositoryDep = Depends(get_admin_mailing_repository)


def get_admin_mailing_service(
    repo: AdminMailingRepository = AdminMailingRepositoryDep,
) -> AdminMailingService:
    """Получить сервис рассылок."""
    return AdminMailingService(repo, TemplateRepository())


AdminMailingServiceDep = Depends(get_admin_mailing_service)


@router.get("/", summary="Список рассылок")
async def list_mailings(
    repo: AdminMailingRepository = AdminMailingRepositoryDep,
) -> list[AdminMailing]:
    """Получить все рассылки."""
    return await repo.list_all()


@router.get("/{admin_mailing_id}/", summary="Получить рассылку")
async def get_mailing(
    admin_mailing_id: UUID,
    repo: AdminMailingRepository = AdminMailingRepositoryDep,
) -> AdminMailing:
    """Получить рассылку по ID."""
    mailing = await repo.get_by_id(admin_mailing_id)
    if mailing is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Mailing not found"
        )
    return mailing


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Создать рассылку",
    description=(
        "Если scheduled_at не указан, то отправка происходит сразу. "
        "Если scheduled_at указан в будущем, то рассылка ждет шедулер."
    ),
)
async def create_mailing(
    data: AdminMailingCreate,
    mailing_service: AdminMailingService = AdminMailingServiceDep,
) -> list[AdminMailing]:
    """Создать ручную рассылку.

    При scheduled_local_time вместо scheduled_at аудитория разбивается по
    таймзонам, встречающимся среди подходящих под audience_filter пользователей:
    на каждую таймзону создаётся своя отдельная рассылка.
    """
    try:
        return await mailing_service.create(
            data.template_id,
            data.audience_filter.model_dump(exclude_none=True),
            data.payload,
            data.scheduled_at,
            data.scheduled_local_time,
            data.created_by,
        )
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {e} not found or inactive",
        ) from e
    except InvalidPayloadError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"payload contains keys not allowed by template: {sorted(e.unknown_keys)}",
        ) from e
    except InvalidScheduledAtError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"scheduled_at must be in the future: {e}",
        ) from e
