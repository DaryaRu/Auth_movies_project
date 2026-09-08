"""Схемы для настроек уведомлений пользователя."""

from uuid import UUID

from pydantic import BaseModel, Field

from src.core.notification_defaults import notification_defaults


class UserNotificationSettings(BaseModel):
    """Настройки уведомлений пользователя."""

    user_id: UUID
    notifications_enabled: bool = Field(
        default=notification_defaults.NOTIFICATIONS_ENABLED, description="Общее включение уведомлений"
    )
    email_enabled: bool = Field(
        default=notification_defaults.EMAIL_ENABLED, description="Включить email уведомления"
    )
    sms_enabled: bool = Field(
        default=notification_defaults.SMS_ENABLED, description="Включить SMS уведомления"
    )
    push_enabled: bool = Field(
        default=notification_defaults.PUSH_ENABLED, description="Включить push уведомления"
    )

    model_config = {"from_attributes": True}


class NotificationSettingsUpdate(BaseModel):
    """Обновление настроек уведомлений пользователя."""

    notifications_enabled: bool | None = Field(default=None, description="Общее включение уведомлений")
    email_enabled: bool | None = Field(default=None, description="Включить email уведомления")
    sms_enabled: bool | None = Field(default=None, description="Включить SMS уведомления")
    push_enabled: bool | None = Field(default=None, description="Включить push уведомления")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "notifications_enabled": True,
                    "email_enabled": True,
                    "sms_enabled": False,
                    "push_enabled": True,
                }
            ]
        }
    }
