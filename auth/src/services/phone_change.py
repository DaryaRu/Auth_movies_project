import logging
import secrets
from uuid import UUID

from redis.asyncio import Redis

from src.core.config import settings
from src.exceptions import (
    NoPendingPhoneChangeException,
    SendCooldownException,
    TooManyAttemptsException,
)
from src.integrations.sms.base_provider import SMSProviderBase


class PhoneChangeService:
    """Смена номера телефона с подтверждением СМС-кодом."""

    def __init__(self, sms_provider: SMSProviderBase, redis: Redis) -> None:
        self._sms_provider = sms_provider
        self._redis = redis

    async def request_change(self, user_id: UUID, new_phone: str) -> None:
        """Генерирует код, сохраняет его вместе с new_phone в Redis и
        отправляет на новый номер. Повторный вызов для того же user_id
        перезаписывает предыдущий запрос (в том числе new_phone) и сбрасывает
        счетчик попыток. Отправка ограничена дважды: кулдаун (PHONE_CHANGE_SEND_COOLDOWN_SECONDS)
        и лимит отправок за фиксированный интервал на номер (PHONE_CHANGE_MAX_SENDS_PER_WINDOW за
        PHONE_CHANGE_SEND_RATE_WINDOW_SECONDS)."""
        cooldown_key = f"phone_change_send_cooldown:{new_phone}"
        cooldown_ttl = await self._redis.ttl(cooldown_key)
        if cooldown_ttl > 0:
            logging.warning(
                f"Слишком частый запрос смены телефона на номер {new_phone}"
            )
            raise SendCooldownException(cooldown_ttl)

        rate_key = f"phone_change_send_rate:{new_phone}"
        sends = await self._redis.get(rate_key)
        if sends and int(sends) >= settings.PHONE_CHANGE_MAX_SENDS_PER_WINDOW:
            logging.warning(
                f"Превышен лимит отправки кода смены на номер {new_phone}"
            )
            raise TooManyAttemptsException()

        code = f"{secrets.randbelow(1000000):06d}"
        key = f"phone_change:{user_id}"
        attempts_key = f"phone_change_attempts:{user_id}"

        pipe = self._redis.pipeline()
        pipe.hset(key, mapping={"new_phone": new_phone, "sms_code": code})
        pipe.expire(key, settings.PHONE_CHANGE_CODE_EXPIRE_SECONDS)
        pipe.delete(attempts_key)
        await pipe.execute()

        # Кулдаун/лимит отправок за фиксированный интервал фиксируются только при успешной отправке.
        await self._sms_provider.send_code(new_phone, code)

        pipe = self._redis.pipeline()
        pipe.incr(rate_key)
        pipe.setex(
            cooldown_key, settings.PHONE_CHANGE_SEND_COOLDOWN_SECONDS, "1"
        )
        await pipe.execute()
        if sends is None:
            await self._redis.expire(
                rate_key, settings.PHONE_CHANGE_SEND_RATE_WINDOW_SECONDS
            )

        logging.info(f"Код смены телефона отправлен пользователю {user_id}")

    async def confirm_change(self, user_id: UUID, code: str) -> str | None:
        """Сверяет код с сохраненным в Redis. При совпадении удаляет запись
        (и счетчик попыток) и возвращает new_phone для записи в БД. При
        несовпадении возвращает None, запись остается, можно повторить
        попытку в пределах PHONE_CHANGE_MAX_ATTEMPTS."""
        attempts_key = f"phone_change_attempts:{user_id}"
        attempts = await self._redis.get(attempts_key)
        if attempts and int(attempts) >= settings.PHONE_CHANGE_MAX_ATTEMPTS:
            logging.warning(
                f"Превышен лимит попыток смены телефона для {user_id}"
            )
            raise TooManyAttemptsException()

        key = f"phone_change:{user_id}"
        data = await self._redis.hgetall(key)
        if not data:
            logging.warning(
                f"Нет активного запроса смены телефона для {user_id}"
            )
            raise NoPendingPhoneChangeException()

        if not secrets.compare_digest(data["sms_code"], code):
            pipe = self._redis.pipeline()
            pipe.incr(attempts_key)
            pipe.expire(
                attempts_key, settings.PHONE_CHANGE_CODE_EXPIRE_SECONDS
            )
            await pipe.execute()
            logging.warning(f"Неверный код смены телефона для {user_id}")
            return None

        await self._redis.delete(key, attempts_key)
        logging.info(f"Смена телефона подтверждена для {user_id}")
        return data["new_phone"]
