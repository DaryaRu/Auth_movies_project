import logging
import secrets
from uuid import UUID

from redis.asyncio import Redis

from src.core.config import settings
from src.exceptions import (
    EmailRequiredForPhoneChangeException,
    NoPendingPhoneChangeException,
    SendCooldownException,
    TooManyAttemptsException,
)
from src.integrations.sms.base_provider import SMSProviderBase
from src.utils.notifications import notify_user


class PhoneChangeService:
    """Смена номера телефона с двойным подтверждением: СМС-код на новый
    номер (владение номером) + код на текущий email (владение аккаунтом)."""

    def __init__(self, sms_provider: SMSProviderBase, redis: Redis) -> None:
        self._sms_provider = sms_provider
        self._redis = redis

    async def request_change(
        self, user_id: UUID, new_phone: str, email: str | None
    ) -> None:
        """Генерирует два независимых кода (для СМС и для email), сохраняет
        их вместе с new_phone в Redis и отправляет каждый на свой канал.
        Повторный вызов для того же user_id перезаписывает предыдущий запрос
        (в том числе new_phone) и сбрасывает счетчик попыток. Отправка на
        номер ограничена дважды: кулдаун (PHONE_CHANGE_SEND_COOLDOWN_SECONDS)
        и лимит отправок за фиксированный интервал (PHONE_CHANGE_MAX_SENDS_PER_WINDOW
        за PHONE_CHANGE_SEND_RATE_WINDOW_SECONDS).

        Raises:
            EmailRequiredForPhoneChangeException: На аккаунте не указан email
                — отправить код подтверждения владения аккаунтом некуда.
        """
        if not email:
            raise EmailRequiredForPhoneChangeException()

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

        sms_code = f"{secrets.randbelow(1000000):06d}"
        email_code = f"{secrets.randbelow(1000000):06d}"
        key = f"phone_change:{user_id}"
        attempts_key = f"phone_change_attempts:{user_id}"

        pipe = self._redis.pipeline()
        pipe.hset(
            key,
            mapping={
                "new_phone": new_phone,
                "sms_code": sms_code,
                "email_code": email_code,
            },
        )
        pipe.expire(key, settings.PHONE_CHANGE_CODE_EXPIRE_SECONDS)
        pipe.delete(attempts_key)
        await pipe.execute()

        # Кулдаун, лимит отправок за фиксированный интервал фиксируются только
        # при успешной отправке обоих кодов.
        await notify_user(
            user_id,
            "phone_change_code",
            payload={"code": email_code},
            required=True,
        )
        await self._sms_provider.send_code(new_phone, sms_code)

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

        logging.info(f"Коды смены телефона отправлены пользователю {user_id}")

    async def confirm_change(
        self, user_id: UUID, sms_code: str, email_code: str
    ) -> str | None:
        """Сверяет оба кода с сохраненными в Redis. При совпадении обоих
        удаляет запись (и счетчик попыток) и возвращает new_phone для записи
        в БД. При несовпадении хотя бы одного возвращает None, запись
        остается, можно повторить попытку в пределах PHONE_CHANGE_MAX_ATTEMPTS."""
        attempts_key = f"phone_change_attempts:{user_id}"
        attempts = await self._redis.get(attempts_key)
        if attempts and int(attempts) >= settings.PHONE_CHANGE_MAX_ATTEMPTS:
            logging.warning(
                f"Превышен лимит попыток смены телефона для {user_id}"
            )
            raise TooManyAttemptsException()

        key = f"phone_change:{user_id}"
        data = await self._redis.hgetall(key)  # type: ignore[misc]
        if not data:
            logging.warning(
                f"Нет активного запроса смены телефона для {user_id}"
            )
            raise NoPendingPhoneChangeException()

        sms_ok = secrets.compare_digest(data["sms_code"], sms_code)
        email_ok = secrets.compare_digest(data["email_code"], email_code)
        if not (sms_ok and email_ok):
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
