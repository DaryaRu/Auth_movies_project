"""Интерфейс отправителя уведомления."""

from typing import Protocol


class Sender(Protocol):
    """Отправляет отрендеренный текст получателю."""

    async def send(
        self, delivery_address: str, subject: str | None, body: str
    ) -> None:
        """Отправить сообщение. Бросает исключение при неудаче."""
        ...
