"""Abstract base class for ETL state storage."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseStorage(ABC):
    """Abstract storage for ETL state persistence."""

    @abstractmethod
    def save_state(self, state: Dict[str, Any]) -> None:
        """Save the current state to the backing storage."""

        raise NotImplementedError

    @abstractmethod
    def retrieve_state(self) -> Dict[str, Any]:
        """Load the saved state from the backing storage."""

        raise NotImplementedError
