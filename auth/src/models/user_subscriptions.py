"""Модель подписки пользователя."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.databases.pg import Base, BaseORM


class UserSubscriptionORM(Base, BaseORM):
    __tablename__ = "user_subscriptions"
    __table_args__ = (
        Index("ix_user_subscriptions_user_id", "user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    subscription_id: Mapped[UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="RESTRICT")
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["UserORM"] = relationship(back_populates="subscriptions")
    subscription: Mapped["SubscriptionORM"] = relationship()
