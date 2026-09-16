import logging
import secrets
from uuid import UUID

from redis.asyncio import Redis

from src.core.config import settings
from src.exceptions import (
    NoPendingEmailChangeException,
    SendCooldownException,
    TooManyAttemptsException,
)
from src.utils.notifications import notify_address, notify_user


class EmailChangeService:
    """Смена email с двойным подтверждением: сначала код на текущий email,
    а после его подтверждения код на новый адрес.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def request_change(self, user_id: UUID, new_email: str) -> None:
        """Генерирует код для старого email, сохраняет его вместе с
        new_email в Redis и отправляет на текущий адрес аккаунта.
        """
        cooldown_key = f"email_change_send_cooldown_old:{user_id}"
        cooldown_ttl = await self._redis.ttl(cooldown_key)
        if cooldown_ttl > 0:
            logging.warning(
                f"Слишком частый запрос смены email для пользователя {user_id}"
            )
            raise SendCooldownException(cooldown_ttl)

        rate_key = f"email_change_send_rate_old:{user_id}"
        sends = await self._redis.get(rate_key)
        if sends and int(sends) >= settings.EMAIL_CHANGE_MAX_SENDS_PER_WINDOW:
            logging.warning(
                f"Превышен лимит отправки кода смены email для {user_id}"
            )
            raise TooManyAttemptsException()

        old_email_code = f"{secrets.randbelow(1000000):06d}"
        key = f"email_change:{user_id}"
        attempts_key = f"email_change_attempts:{user_id}"

        pipe = self._redis.pipeline()
        pipe.delete(key)
        pipe.hset(
            key,
            mapping={"new_email": new_email, "old_email_code": old_email_code},
        )
        pipe.expire(key, settings.EMAIL_CHANGE_CODE_EXPIRE_SECONDS)
        pipe.delete(attempts_key)
        await pipe.execute()

        await notify_user(
            user_id,
            "email_change_code_old",
            payload={"code": old_email_code, "new_email": new_email},
            required=True,
        )

        pipe = self._redis.pipeline()
        pipe.incr(rate_key)
        pipe.setex(
            cooldown_key, settings.EMAIL_CHANGE_SEND_COOLDOWN_SECONDS, "1"
        )
        await pipe.execute()
        if sends is None:
            await self._redis.expire(
                rate_key, settings.EMAIL_CHANGE_SEND_RATE_WINDOW_SECONDS
            )

        logging.info(f"Код смены email отправлен {user_id} на старый адрес")

    async def verify_old_email(
        self, user_id: UUID, old_email_code: str
    ) -> bool:
        """Сверяет код со старого email. При совпадении генерирует и
        отправляет код на новый адрес, возвращает True. При несовпадении
        увеличивает счетчик попыток и возвращает False, запись остается,
        можно повторить в пределах EMAIL_CHANGE_MAX_ATTEMPTS.
        """
        attempts_key = f"email_change_attempts:{user_id}"
        attempts = await self._redis.get(attempts_key)
        if attempts and int(attempts) >= settings.EMAIL_CHANGE_MAX_ATTEMPTS:
            logging.warning(
                f"Превышен лимит попыток смены email для {user_id}"
            )
            raise TooManyAttemptsException()

        key = f"email_change:{user_id}"
        data = await self._redis.hgetall(key)  # type: ignore[misc]
        if not data or "old_email_code" not in data:
            logging.warning(f"Нет активного запроса смены email для {user_id}")
            raise NoPendingEmailChangeException()

        if not secrets.compare_digest(data["old_email_code"], old_email_code):
            pipe = self._redis.pipeline()
            pipe.incr(attempts_key)
            pipe.expire(
                attempts_key, settings.EMAIL_CHANGE_CODE_EXPIRE_SECONDS
            )
            await pipe.execute()
            logging.warning(
                f"Неверный код старого email при смене для {user_id}"
            )
            return False

        new_email = data["new_email"]

        cooldown_key = f"email_change_send_cooldown_new:{new_email}"
        cooldown_ttl = await self._redis.ttl(cooldown_key)
        if cooldown_ttl > 0:
            logging.warning(
                f"Слишком частый запрос кода на новый email {new_email}"
            )
            raise SendCooldownException(cooldown_ttl)

        rate_key = f"email_change_send_rate_new:{new_email}"
        sends = await self._redis.get(rate_key)
        if sends and int(sends) >= settings.EMAIL_CHANGE_MAX_SENDS_PER_WINDOW:
            logging.warning(
                f"Превышен лимит отправки кода на новый email {new_email}"
            )
            raise TooManyAttemptsException()

        new_email_code = f"{secrets.randbelow(1000000):06d}"
        pipe = self._redis.pipeline()
        pipe.hset(key, "new_email_code", new_email_code)
        pipe.expire(key, settings.EMAIL_CHANGE_CODE_EXPIRE_SECONDS)
        pipe.delete(attempts_key)
        await pipe.execute()

        await notify_address(
            user_id,
            "email_change_code_new",
            new_email,
            payload={"code": new_email_code},
        )

        pipe = self._redis.pipeline()
        pipe.incr(rate_key)
        pipe.setex(
            cooldown_key, settings.EMAIL_CHANGE_SEND_COOLDOWN_SECONDS, "1"
        )
        await pipe.execute()
        if sends is None:
            await self._redis.expire(
                rate_key, settings.EMAIL_CHANGE_SEND_RATE_WINDOW_SECONDS
            )

        logging.info(f"Код смены email отправлен {user_id} на новый адрес")
        return True

    async def verify_new_email(
        self, user_id: UUID, new_email_code: str
    ) -> str | None:
        """Сверяет код с нового email. При совпадении удаляет запись и
        возвращает new_email для записи в БД. При несовпадении увеличивает
        счетчик попыток и возвращает None, запись остается.
        """
        attempts_key = f"email_change_attempts:{user_id}"
        attempts = await self._redis.get(attempts_key)
        if attempts and int(attempts) >= settings.EMAIL_CHANGE_MAX_ATTEMPTS:
            logging.warning(
                f"Превышен лимит попыток смены email для {user_id}"
            )
            raise TooManyAttemptsException()

        key = f"email_change:{user_id}"
        data = await self._redis.hgetall(key)  # type: ignore[misc]
        if not data or "new_email_code" not in data:
            logging.warning(
                f"Нет ожидающего кода на новый email для {user_id}"
            )
            raise NoPendingEmailChangeException()

        if not secrets.compare_digest(data["new_email_code"], new_email_code):
            pipe = self._redis.pipeline()
            pipe.incr(attempts_key)
            pipe.expire(
                attempts_key, settings.EMAIL_CHANGE_CODE_EXPIRE_SECONDS
            )
            await pipe.execute()
            logging.warning(
                f"Неверный код нового email при смене для {user_id}"
            )
            return None

        await self._redis.delete(key, attempts_key)
        logging.info(f"Смена email подтверждена для {user_id}")
        return data["new_email"]
