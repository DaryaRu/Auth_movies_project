"""Модель типа подписки."""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.databases.pg import Base, BaseORM


class SubscriptionORM(Base, BaseORM):
    __tablename__ = "subscriptions"

    code: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(default=True)
