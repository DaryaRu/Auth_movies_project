import logging
import secrets
from uuid import UUID

from redis.asyncio import Redis

from src.core.config import settings
from src.exceptions import TooManyAttemptsException
from src.integrations.sms.base_provider import SMSProviderBase

MAX_ATTEMPTS = 5


class TwoFactorService:
    def __init__(self, sms_provider: SMSProviderBase, redis: Redis) -> None:
        self._sms_provider = sms_provider
        self._redis = redis

    async def send_code(self, user_id: UUID, phone: str) -> None:
        """Генерирует 6-значный код, сохраняет в Redis с TTL и
        отправляет на указанный номер. Повторный вызов для того же user_id перезаписывает
        предыдущий код и сбрасывает счетчик попыток."""
        code = f"{secrets.randbelow(1000000):06d}"
        # ключи Redis для пользователя: один под сам код, другой под счетчик попыток
        code_key = f"2fa_code:{user_id}"
        attempts_key = f"2fa_attempts:{user_id}"

        pipe = self._redis.pipeline()
        pipe.setex(code_key, settings.CODE_2FA_EXPIRE_SECONDS, code)
        pipe.delete(attempts_key)
        await pipe.execute()

        await self._sms_provider.send_code(phone, code)
        logging.info(f"2FA-код отправлен пользователю {user_id}")

    async def verify_code(self, user_id: UUID, code: str) -> bool:
        """Сверяет код с сохраненным в Redis. Код (и счетчик попыток) удаляется только при совпадении, при несовпадении
        остается в Redis, чтобы можно было повторить попытку в пределах MAX_ATTEMPTS для текущего кода;
        после лимита — TooManyAttemptsException, новый код нужно запросить заново."""
        attempts_key = f"2fa_attempts:{user_id}"
        attempts = await self._redis.get(attempts_key)
        if attempts and int(attempts) >= MAX_ATTEMPTS:
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
