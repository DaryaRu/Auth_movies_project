"""Email-отправитель через SMTP."""

from email.message import EmailMessage

import aiosmtplib
from core.settings import settings


class EmailSender:
    """Отправка email через SMTP."""

    async def send(
        self, delivery_address: str, subject: str | None, body: str
    ) -> None:
        """Собирает и отправляет письмо. Бросает исключение при сбое SMTP."""
        message = EmailMessage()
        message["From"] = settings.EMAIL_FROM
        message["To"] = delivery_address
        message["Subject"] = subject or ""
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
        )
