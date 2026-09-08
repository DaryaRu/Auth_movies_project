from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.notification_defaults import notification_defaults
from src.databases.pg import Base, BaseORM

if TYPE_CHECKING:
    from src.models.users import UserORM


class UserNotificationSettingsORM(Base, BaseORM):
    __tablename__ = "user_notification_settings"
    __table_args__ = (
        Index(
            "ix_user_notification_settings_user_id_unique",
            "user_id",
            unique=True,
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        default=notification_defaults.NOTIFICATIONS_ENABLED
    )
    email_enabled: Mapped[bool] = mapped_column(
        default=notification_defaults.EMAIL_ENABLED
    )
    sms_enabled: Mapped[bool] = mapped_column(
        default=notification_defaults.SMS_ENABLED
    )
    push_enabled: Mapped[bool] = mapped_column(
        default=notification_defaults.PUSH_ENABLED
    )

    user: Mapped["UserORM"] = relationship(back_populates="notification_settings")
