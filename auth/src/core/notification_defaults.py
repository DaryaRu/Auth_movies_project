"""Дефолтные значения для настроек уведомлений пользователя."""

from pydantic import BaseModel


class NotificationDefaults(BaseModel):
    """Дефолтные значения для настроек уведомлений."""

    NOTIFICATIONS_ENABLED: bool = True
    EMAIL_ENABLED: bool = True
    SMS_ENABLED: bool = False
    PUSH_ENABLED: bool = True

    def to_dict(self) -> dict:
        """Словарь {поле: значение} для использования в SQL/ORM."""
        return {
            "notifications_enabled": self.NOTIFICATIONS_ENABLED,
            "email_enabled": self.EMAIL_ENABLED,
            "sms_enabled": self.SMS_ENABLED,
            "push_enabled": self.PUSH_ENABLED,
        }


notification_defaults = NotificationDefaults()