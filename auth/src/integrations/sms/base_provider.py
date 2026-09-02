from abc import ABC, abstractmethod


class SMSProviderBase(ABC):
    """Интерфейс СМС-провайдера для доставки кода подтверждения."""

    @abstractmethod
    async def send_code(self, phone: str, code: str) -> None:
        """Отправляет code на номер телефона. Бросает ProviderException при ошибке отправки."""
        raise NotImplementedError
