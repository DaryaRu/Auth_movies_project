from abc import ABC, abstractmethod

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.core.config import settings


class BaseHashService(ABC):
    @abstractmethod
    def create_hash_password(self, password: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify_password(
        self,
        plain_password: str,
        hashed_password: str,
    ) -> bool:
        raise NotImplementedError


class HashArgon2Service(BaseHashService):
    """
    Сервис для хеширования паролей с использованием Argon2 (argon2id).
    """

    def __init__(self) -> None:
        self.hasher = PasswordHasher(
            time_cost=settings.HASH_TIME_COST,
            memory_cost=settings.HASH_MEMORY_COST,
            parallelism=settings.HASH_PARALLELISM,
        )

    def create_hash_password(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return self.hasher.verify(hashed_password, plain_password)
        except VerifyMismatchError:
            return False
