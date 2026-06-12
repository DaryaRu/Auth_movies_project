from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.databases.pg import Base, BaseORM
from src.models.associations import role_permissions_table, user_roles_table


class RoleORM(Base, BaseORM):
    """
    Роль пользователя в системе.

    Атрибуты:
        name: Название роли.
        description: Описание роли.
        is_active: Флаг активности (если роль деактивировать,
            то прав у пользователей с этой ролью не будет).
        is_system: Флаг системной роли, не может быть удалена через API
            (защита от случайного удаления критичных ролей).
        users: Пользователи с данной ролью.
        permissions: Права для этой роли.
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    users: Mapped[list["UserORM"]] = relationship(
        secondary=user_roles_table,
        back_populates="roles",
    )
    permissions: Mapped[list["PermissionORM"]] = relationship(
        secondary=role_permissions_table,
        back_populates="roles",
    )
