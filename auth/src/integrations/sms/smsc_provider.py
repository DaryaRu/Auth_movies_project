import logging

import aiohttp
from src.core.config import settings
from src.exceptions import ProviderException
from src.integrations.sms.base_provider import SMSProviderBase


class SMSCProvider(SMSProviderBase):
    """СМС-провайдер SMSC.ru. В тестовом режиме (SMSC_TEST_MODE) сообщения
    проходят все стадии обработки, но не отправляются абоненту, оплата не списывается."""

    async def send_code(self, phone: str, code: str) -> None:
        """Отправляет код на номер через SMSC.ru.

        Используется таймаут запроса (10 секунд). Без него при зависании SMSC auth-service мог бы
        ждать ответа до 5 минут (дефолт aiohttp), занимая воркер gunicorn, и проиграть
        гонку proxy_read_timeout nginx. Клиент получил бы 502 от nginx.
        """
        params = {
            "login": settings.SMSC_LOGIN,
            "psw": settings.SMSC_PASSWORD,
            "phones": phone,
            "mes": f"Код подтверждения: {code}",
            "fmt": 3,
        }
        if settings.SMSC_SENDER_NAME:
            params["sender"] = settings.SMSC_SENDER_NAME
        if settings.SMSC_TEST_MODE:
            params["test"] = 1

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.get(
                    "https://smsc.ru/sys/send.php", params=params
                ) as response:
                    data = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            logging.error(f"Ошибка соединения с SMSC: {exc!r}")
            raise ProviderException(
                f"Ошибка соединения с СМС-провайдером: {exc}"
            ) from exc

        if response.status >= 400 or "error" in data:
            logging.error(
                "Не удалось отправить СМС через SMSC: "
                f"status_code={response.status}, {data=}"
            )
            error_text = data.get("error", "неизвестная ошибка")
            error_code = data.get("error_code")
            raise ProviderException(
                f"Ошибка СМС-провайдера: {error_text} (код {error_code})"
            )
