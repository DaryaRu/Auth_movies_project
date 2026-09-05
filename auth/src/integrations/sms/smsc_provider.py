import logging

import aiohttp
from src.core.config import settings
from src.exceptions import ProviderException
from src.integrations.sms.base_provider import SMSProviderBase
from src.utils.backoff import async_backoff


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
            data, status = await self._request(params)
        except (aiohttp.ClientError, TimeoutError) as exc:
            logging.error(f"Ошибка соединения с SMSC: {exc!r}")
            raise ProviderException(
                f"Ошибка соединения с СМС-провайдером: {exc}"
            ) from exc

        if status >= 400 or "error" in data:
            logging.error(
                "Не удалось отправить СМС через SMSC: "
                f"status_code={status}, {data=}"
            )
            error_text = data.get("error", "неизвестная ошибка")
            error_code = data.get("error_code")
            raise ProviderException(
                f"Ошибка СМС-провайдера: {error_text} (код {error_code})"
            )

    @async_backoff(exceptions=(aiohttp.ClientError, TimeoutError))
    async def _request(self, params: dict) -> tuple[dict, int]:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        ) as session:
            async with session.get(
                "https://smsc.ru/sys/send.php", params=params
            ) as response:
                return await response.json(), response.status
