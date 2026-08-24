"""API endpoints для CRUD шаблонов уведомлений (для админки)."""

from uuid import UUID

from asyncpg.exceptions import UniqueViolationError
from fastapi import APIRouter, Depends, HTTPException, status
from jinja2.exceptions import UndefinedError

from src.api.v1.dependencies import InternalServiceDep, StaffUserDep
from src.repositories.templates import TemplateRepository
from src.schemas.templates import (
    Template,
    TemplateCreate,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateUpdate,
)
from src.services.notifications import (
    InvalidPayloadError,
    TemplateNotFoundError,
)
from src.services.templates import TemplateService
from src.validators import TemplateValidationError, validate_template_content

router = APIRouter(prefix="/notifications/templates", tags=["templates"])


def get_template_repository() -> TemplateRepository:
    """Получить репозиторий шаблонов."""
    return TemplateRepository()


TemplateRepositoryDep = Depends(get_template_repository)


def get_template_service(
    repo: TemplateRepository = TemplateRepositoryDep,
) -> TemplateService:
    """Получить сервис шаблонов."""
    return TemplateService(repo)


TemplateServiceDep = Depends(get_template_service)


@router.get("/", summary="Список шаблонов")
async def list_templates(
    _: StaffUserDep,
    repo: TemplateRepository = TemplateRepositoryDep,
) -> list[Template]:
    """Вернуть все шаблоны."""
    return await repo.list_all()


@router.get("/by-code/{code}/", summary="Получить шаблон по code")
async def get_template_by_code(
    code: str,
    _: InternalServiceDep,
    repo: TemplateRepository = TemplateRepositoryDep,
) -> Template:
    """Получить шаблон по code."""
    template = await repo.get_by_code(code)
    if template is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return template


@router.get("/{template_id}/", summary="Получить шаблон")
async def get_template(
    template_id: UUID,
    _: StaffUserDep,
    repo: TemplateRepository = TemplateRepositoryDep,
) -> Template:
    """Вернуть шаблон по ID."""
    template = await repo.get_by_id(template_id)
    if template is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return template


@router.post(
    "/", status_code=status.HTTP_201_CREATED, summary="Создать шаблон"
)
async def create_template(
    template: TemplateCreate,
    _: StaffUserDep,
    repo: TemplateRepository = TemplateRepositoryDep,
) -> Template:
    """Создать новый шаблон."""
    try:
        validate_template_content(
            template.subject, template.body, template.allowed_variables
        )
    except TemplateValidationError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e

    try:
        return await repo.create(template.model_dump())
    except UniqueViolationError as e:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Template with code '{template.code}' already exists",
        ) from e


@router.patch("/{template_id}/", summary="Отредактировать шаблон")
async def update_template(
    template_id: UUID,
    template: TemplateUpdate,
    _: StaffUserDep,
    repo: TemplateRepository = TemplateRepositoryDep,
) -> Template:
    """Отредактировать шаблон."""
    existing = await repo.get_by_id(template_id)
    if existing is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    update_data = template.model_dump(exclude_unset=True)
    if not update_data:
        return existing

    try:
        validate_template_content(
            update_data.get("subject", existing.subject),
            update_data.get("body", existing.body),
            update_data.get("allowed_variables", existing.allowed_variables),
        )
    except TemplateValidationError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e

    updated = await repo.update(template_id, update_data)
    assert updated is not None
    return updated


@router.post(
    "/{template_id}/preview/",
    summary="Превью рендера шаблона с тестовым payload",
)
async def preview_template(
    template_id: UUID,
    request: TemplatePreviewRequest,
    _: StaffUserDep,
    template_service: TemplateService = TemplateServiceDep,
) -> TemplatePreviewResponse:
    """Отрендерить шаблон для превью в админке."""
    try:
        return await template_service.preview(template_id, request.payload)
    except TemplateNotFoundError as e:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Template {e} not found"
        ) from e
    except InvalidPayloadError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"payload contains keys not allowed by template: {sorted(e.unknown_keys)}",
        ) from e
    except UndefinedError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"payload is missing a variable required by the template: {e}",
        ) from e
