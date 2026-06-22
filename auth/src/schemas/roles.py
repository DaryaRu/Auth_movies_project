from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.permissions import PermissionResponseScheme

ROLE_EXAMPLE = {
    "name": "premium_subscriber",
    "description": "Пользователь с подпиской Premium",
    "is_active": True,
}


class RoleCreateScheme(BaseModel):
    """Схема для создания роли.

    Атрибуты:
        name (str): Название роли.
        description (str | None): Описание роли.
        is_active (bool): Активна ли роль (по умолчанию — True).
    """

    model_config = ConfigDict(
        json_schema_extra={"example": ROLE_EXAMPLE}
    )

    name: str = Field(..., description="Название роли", max_length=100)
    description: str | None = Field(None, description="Описание роли")
    is_active: bool = Field(True, description="Активна ли роль")


class RoleUpdateScheme(BaseModel):
    """Схема для обновления роли.

    Атрибуты:
        name (str | None): Новое название роли.
        description (str | None): Новое описание.
        is_active (bool | None): Новый статус активности.
    """

    model_config = ConfigDict(
        json_schema_extra={"example": ROLE_EXAMPLE}
    )

    name: str | None = Field(None, description="Новое название роли", max_length=100)
    description: str | None = Field(None, description="Новое описание роли")
    is_active: bool | None = Field(None, description="Новый статус активности")


class RoleResponseScheme(BaseModel):
    """Схема ответа с данными роли.

    Атрибуты:
        id (UUID): Уникальный идентификатор роли.
        name (str): Название роли.
        description (str | None): Описание роли.
        is_active (bool): Активна ли роль.
        is_system (bool): Системная ли роль (нельзя удалить через API).
    """

    id: UUID
    name: str
    description: str | None
    is_active: bool
    is_system: bool

    model_config = ConfigDict(from_attributes=True)


class RoleDetailScheme(RoleResponseScheme):
    """Схема ответа с детальными данными роли, включая список прав."""

    permissions: list[PermissionResponseScheme] = []
