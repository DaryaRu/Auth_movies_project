from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.databases.pg import Base, BaseORM
from src.models.associations import role_permissions_table


class PermissionORM(Base, BaseORM):
    """
    Права доступа в системе определяют, какие действия
    доступны пользователям с определённой ролью.

    Атрибуты:
        code: Уникальный код права в формате «область системы:что именно разрешено».
            Например: admin:manage_roles, user:view, content:upload, movie:watch.
            Используется для проверки доступа.
        name: Название.
        description: Описание того, что даёт право.
        category: Группа для фильтрации в админке. По умолчанию — general.
        roles: Роли, для которых действует право.
    """

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general", index=True)

    roles: Mapped[list["RoleORM"]] = relationship(
        secondary=role_permissions_table,
        back_populates="permissions",
    )
