from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from src.databases.pg import Base, BaseORM


class UserORM(Base, BaseORM):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email_unique", "email", unique=True),
    )

    email: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_superuser: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
