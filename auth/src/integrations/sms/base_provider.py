from abc import ABC, abstractmethod


class SMSProviderBase(ABC):
    @abstractmethod
    async def send_code(self, phone: str, code: str) -> None:
        raise NotImplementedError
