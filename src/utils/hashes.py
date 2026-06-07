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


# class HashBcryptService(BaseHashService):
#     """
#     Сервис для работы с хешированием и проверкой паролей.
#     Использует библиотеку `passlib` и алгоритм bcrypt для безопасного хранения паролей.
#     """

#     pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#     def create_hash_password(self, password: str) -> str:
#         """
#         Создает хеш для переданного пароля.
#         Args:
#             password (str): Пароль.

#         Returns:
#             str: Хэш пароля.
#         """
#         return self.pwd_context.hash(password)

#     def verify_password(
#         self, plain_password: str, hashed_password: str
#     ) -> bool:
#         """
#         Проверяет соответствие пароля и его хеша.
#         Args:
#             plain_password (str): Пароль.
#             hashed_password (str): Хеш пароля, сохраненный в БД у пользователя.
#         Returns:
#             bool: True, если пароль корректный, иначе False.
#         """
#         return self.pwd_context.verify(plain_password, hashed_password)


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
