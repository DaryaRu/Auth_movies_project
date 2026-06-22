from sqlalchemy import Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.databases.pg import Base, BaseORM
from src.models.associations import user_roles_table


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
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    is_superuser: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    roles: Mapped[list["RoleORM"]] = relationship(
        secondary=user_roles_table,
        back_populates="users",
    )
    oauth_accounts: Mapped[list["OAuthAccountORM"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
