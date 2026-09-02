import logging

import aiohttp
from src.core.config import settings
from src.exceptions import ProviderException
from src.integrations.sms.base_provider import SMSProviderBase


class SMSCProvider(SMSProviderBase):
    """СМС-провайдер SMSC.ru. В тестовом режиме (SMSC_TEST_MODE) сообщения
    проходят все стадии обработки, но не отправляются абоненту, оплата не списывается."""

    async def send_code(self, phone: str, code: str) -> None:
        params = {
            "login": settings.SMSC_LOGIN,
            "psw": settings.SMSC_PASSWORD,
            "phones": phone,
            "mes": f"Код подтверждения: {code}",
            "fmt": 3,
        }
        if settings.SMSC_TEST_MODE:
            params["test"] = 1

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://smsc.ru/sys/send.php", params=params
            ) as response:
                data = await response.json()
                if response.status >= 400 or "error" in data:
                    logging.error(
                        "Не удалось отправить СМС через SMSC: "
                        f"status_code={response.status}, {data=}"
                    )
                    raise ProviderException()
