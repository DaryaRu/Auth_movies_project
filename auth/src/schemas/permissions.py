import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CODE_REGEX = re.compile(r"^[a-z0-9_]+:[a-z0-9_]+$")

PERMISSION_EXAMPLE = {
    "code": "movie:watch_premium",
    "name": "Смотреть премиум-контент",
    "description": "Доступ к фильмам по подписке Premium",
    "category": "movies",
}


def _validate_code(v: str | None) -> str | None:
    if v is not None and not CODE_REGEX.match(v):
        raise ValueError(
            "code должен быть в формате «область системы:действие» — "
            "только строчные буквы, цифры и подчёркивания, например: movie:watch"
        )
    return v


class PermissionCreateScheme(BaseModel):
    """Схема для создания права.

    Атрибуты:
        code (str): Уникальный код права, например movie:watch_premium.
        name (str): Название права.
        description (str | None): Описание того, что даёт право.
        category (str): Группа для фильтрации (по умолчанию — general).
    """

    model_config = ConfigDict(
        json_schema_extra={"example": PERMISSION_EXAMPLE}
    )

    code: str = Field(
        ...,
        description="Код права в формате «область системы:действие», например: movie:watch, admin:manage_roles, content:upload",
        max_length=100,
    )
    name: str = Field(..., description="Название права", max_length=150)
    description: str | None = Field(
        None, description="Описание того, что даёт право"
    )
    category: str = Field(
        "general",
        description="Группа для группировки при отображении списка прав",
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
        description="Новый код права в формате «область системы:действие», например: movie:watch, admin:manage_roles",
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
