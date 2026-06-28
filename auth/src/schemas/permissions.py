import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CODE_REGEX = re.compile(r"^[a-z0-9_]+:[a-z0-9_]+$")

PERMISSION_EXAMPLE = {
    "code": "content:edit",
    "name": "Редактировать фильмы",
    "description": "Позволяет редактировать карточки фильмов в каталоге",
    "category": "content",
}


def _validate_code(v: str | None) -> str | None:
    if v is not None and not CODE_REGEX.match(v):
        raise ValueError(
            "code должен быть в формате «область системы:действие» — "
            "только строчные буквы, цифры и подчёркивания, например: content:edit"
        )
    return v


class PermissionCreateScheme(BaseModel):
    """Схема для создания права.

    Права определяют административные действия для ролей.

    Атрибуты:
        code (str): Уникальный код права в формате «область:действие», например content:edit, user:view.
        name (str): Название права.
        description (str | None): Описание того, что даёт право.
        category (str): Группа для фильтрации, например content(по умолчанию — general).
    """

    model_config = ConfigDict(
        json_schema_extra={"example": PERMISSION_EXAMPLE}
    )

    code: str = Field(
        ...,
        description="Код права в формате «область:действие», например: content:edit, user:view, stats:view",
        max_length=100,
    )
    name: str = Field(..., description="Название права", max_length=150)
    description: str | None = Field(
        None, description="Описание того, что даёт право"
    )
    category: str = Field(
        "general",
        description="Группа для фильтрации, например content, stats",
        max_length=50,
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        return _validate_code(v)


class PermissionUpdateScheme(BaseModel):
    """Схема для обновления права.

    Атрибуты:
        code (str | None): Новый код права.
        name (str | None): Новое название.
        description (str | None): Новое описание.
        category (str | None): Новая группа.
    """

    model_config = ConfigDict(
        json_schema_extra={"example": PERMISSION_EXAMPLE}
    )

    code: str | None = Field(
        None,
        description="Новый код права в формате «область:действие», например: content:edit, user:view, stats:view",
        max_length=100,
    )
    name: str | None = Field(
        None, description="Новое название права", max_length=150
    )
    description: str | None = Field(None, description="Новое описание права")
    category: str | None = Field(
        None, description="Новая группа", max_length=50
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str | None) -> str | None:
        return _validate_code(v)


class PermissionResponseScheme(BaseModel):
    """Схема ответа с данными права.

    Атрибуты:
        id (UUID): Уникальный идентификатор права.
        code (str): Код права.
        name (str): Название права.
        description (str | None): Описание права.
        category (str): Группа права.
    """

    id: UUID
    code: str
    name: str
    description: str | None
    category: str

    model_config = ConfigDict(from_attributes=True)
