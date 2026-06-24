"""State manager."""

from typing import Any

from state.base import BaseStorage


class State:
    """Keep a copy of state and sync it with storage."""

    def __init__(self, storage: BaseStorage) -> None:
        """Initialize state manager and load existing state from storage."""
        self.storage = storage
        self.state = storage.retrieve_state()

    def set_state(self, key: str, value: Any) -> None:
        """Update the local state and save it."""

        self.state[key] = value
        self.storage.save_state(self.state)

    def get_state(self, key: str) -> Any:
        """Return the value for the requested state key."""

        return self.state.get(key)
