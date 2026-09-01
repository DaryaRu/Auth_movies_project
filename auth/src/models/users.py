from typing import TYPE_CHECKING

from sqlalchemy import Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.databases.pg import Base, BaseORM
from src.models.associations import user_roles_table

if TYPE_CHECKING:
    from src.models.oauth_accounts import OAuthAccountORM
    from src.models.roles import RoleORM
    from src.models.user_subscriptions import UserSubscriptionORM


class UserORM(Base, BaseORM):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "ix_users_email_unique",
            "email",
            unique=True,
            postgresql_where=text("email IS NOT NULL"),
        ),
        Index(
            "ix_users_phone_unique",
            "phone",
            unique=True,
            postgresql_where=text("phone IS NOT NULL"),
        ),
    )

    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    full_name: Mapped[str | None] = mapped_column(String(255))
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    is_superuser: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    email_verified: Mapped[bool] = mapped_column(default=False)
    timezone: Mapped[str | None] = mapped_column(String(64))
    roles: Mapped[list["RoleORM"]] = relationship(
        secondary=user_roles_table,
        back_populates="users",
    )
    oauth_accounts: Mapped[list["OAuthAccountORM"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    subscriptions: Mapped[list["UserSubscriptionORM"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
