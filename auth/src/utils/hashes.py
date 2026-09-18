from abc import ABC, abstractmethod

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from starlette.concurrency import run_in_threadpool

from src.core.config import settings


class BaseHashService(ABC):
    @abstractmethod
    async def create_hash_password(self, password: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def verify_password(
        self,
        plain_password: str,
        hashed_password: str,
    ) -> bool:
        raise NotImplementedError


class HashArgon2Service(BaseHashService):
    """
    Сервис для хеширования паролей с использованием Argon2 (argon2id).

    Выполняются в ограниченном пуле потоков (run_in_threadpool), чтобы не блокировать
    event loop и обработку остальных асинхронных запросов.
    """

    def __init__(self) -> None:
        self.hasher = PasswordHasher(
            time_cost=settings.HASH_TIME_COST,
            memory_cost=settings.HASH_MEMORY_COST,
            parallelism=settings.HASH_PARALLELISM,
        )

    async def create_hash_password(self, password: str) -> str:
        return await run_in_threadpool(self.hasher.hash, password)

    async def verify_password(
        self, plain_password: str, hashed_password: str
    ) -> bool:
        try:
            return await run_in_threadpool(
                self.hasher.verify, hashed_password, plain_password
            )
        except VerifyMismatchError:
            return False
