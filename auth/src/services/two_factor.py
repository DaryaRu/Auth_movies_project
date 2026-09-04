import logging
import secrets
from uuid import UUID

from redis.asyncio import Redis

from src.core.config import settings
from src.exceptions import SendCooldownException, TooManyAttemptsException
from src.integrations.sms.base_provider import SMSProviderBase


class TwoFactorService:
    def __init__(self, sms_provider: SMSProviderBase, redis: Redis) -> None:
        self._sms_provider = sms_provider
        self._redis = redis

    async def send_code(self, user_id: UUID, phone: str) -> None:
        """Генерирует 6-значный код, сохраняет в Redis с TTL и
        отправляет на указанный номер. Повторный вызов для того же user_id перезаписывает
        предыдущий код и сбрасывает счетчик попыток.
        Отправка ограничена кулдауном (нельзя запросить код чаще, чем раз в TWO_FA_SEND_COOLDOWN_SECONDS)
        и частотой на сам номер телефона (TWO_FA_MAX_SENDS_PER_WINDOW за TWO_FA_SEND_RATE_WINDOW_SECONDS)."""
        cooldown_key = f"2fa_send_cooldown:{phone}"
        cooldown_ttl = await self._redis.ttl(cooldown_key)
        if cooldown_ttl > 0:
            logging.warning(f"Слишком частый запрос 2FA-кода на номер {phone}")
            raise SendCooldownException(cooldown_ttl)

        rate_key = f"2fa_send_rate:{phone}"
        sends = await self._redis.get(rate_key)
        if sends and int(sends) >= settings.TWO_FA_MAX_SENDS_PER_WINDOW:
            logging.warning(
                f"Превышен лимит отправки 2FA-кода на номер {phone}"
            )
            raise TooManyAttemptsException()

        code = f"{secrets.randbelow(1000000):06d}"
        # ключи Redis для пользователя: один под сам код, другой под счетчик попыток
        code_key = f"2fa_code:{user_id}"
        attempts_key = f"2fa_attempts:{user_id}"

        pipe = self._redis.pipeline()
        pipe.setex(code_key, settings.CODE_2FA_EXPIRE_SECONDS, code)
        pipe.delete(attempts_key)
        await pipe.execute()

        # Кулдаун/лимит отправок за фиксированный интервал фиксируются только при успешной отправке.
        await self._sms_provider.send_code(phone, code)

        pipe = self._redis.pipeline()
        pipe.incr(rate_key)
        pipe.setex(cooldown_key, settings.TWO_FA_SEND_COOLDOWN_SECONDS, "1")
        await pipe.execute()
        if sends is None:
            await self._redis.expire(
                rate_key, settings.TWO_FA_SEND_RATE_WINDOW_SECONDS
            )

        logging.info(f"2FA-код отправлен пользователю {user_id}")

    async def verify_code(self, user_id: UUID, code: str) -> bool:
        """Сверяет код с сохраненным в Redis. Код (и счетчик попыток) удаляется только при совпадении, при несовпадении
        остается в Redis, чтобы можно было повторить попытку в пределах TWO_FA_MAX_ATTEMPTS для текущего кода;
        после лимита — TooManyAttemptsException, новый код нужно запросить заново."""
        attempts_key = f"2fa_attempts:{user_id}"
        attempts = await self._redis.get(attempts_key)
        if attempts and int(attempts) >= settings.TWO_FA_MAX_ATTEMPTS:
            logging.warning(f"Превышен лимит попыток 2FA для {user_id}")
            raise TooManyAttemptsException()

        code_key = f"2fa_code:{user_id}"
        stored_code = await self._redis.get(code_key)
        if stored_code is None:
            logging.warning(f"2FA-код не найден или истек для {user_id}")
            return False

        if not secrets.compare_digest(stored_code, code):
            pipe = self._redis.pipeline()
            pipe.incr(attempts_key)
            pipe.expire(attempts_key, settings.CODE_2FA_EXPIRE_SECONDS)
            await pipe.execute()
            logging.warning(f"Неверный 2FA-код для {user_id}")
            return False

        await self._redis.delete(code_key, attempts_key)
        logging.info(f"2FA-код подтвержден для {user_id}")
        return True
