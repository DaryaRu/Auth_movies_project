"""API endpoints для CRUD шаблонов уведомлений (для админки)."""

from uuid import UUID

from asyncpg.exceptions import UniqueViolationError
from fastapi import APIRouter, Depends, HTTPException, status

from src.repositories.templates import TemplateRepository
from src.schemas.templates import Template, TemplateCreate, TemplateUpdate

router = APIRouter(prefix="/notifications/templates", tags=["templates"])


def get_template_repository() -> TemplateRepository:
    """Получить репозиторий шаблонов."""
    return TemplateRepository()


TemplateRepositoryDep = Depends(get_template_repository)


@router.get("/", summary="Список шаблонов")
async def list_templates(
    repo: TemplateRepository = TemplateRepositoryDep,
) -> list[Template]:
    """Вернуть все шаблоны."""
    return await repo.list_all()


@router.get("/by-code/{code}/", summary="Получить шаблон по code")
async def get_template_by_code(
    code: str,
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
    repo: TemplateRepository = TemplateRepositoryDep,
) -> Template:
    """Создать новый шаблон."""
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
    repo: TemplateRepository = TemplateRepositoryDep,
) -> Template:
    """Отредактировать шаблон."""
    update_data = template.model_dump(exclude_unset=True)
    updated = (
        await repo.get_by_id(template_id)
        if not update_data
        else await repo.update(template_id, update_data)
    )
    if updated is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return updated
