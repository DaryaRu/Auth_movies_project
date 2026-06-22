"""ETL state storage based on JSON file."""

import json
from pathlib import Path
from typing import Any, Dict

from state.base import BaseStorage


class JsonFileStorage(BaseStorage):
    """Store ETL state in a local JSON file."""

    def __init__(self, file_path: Path) -> None:
        """Initialize storage."""
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: Dict[str, Any]) -> None:
        """Write the provided state to the JSON file."""

        self.file_path.write_text(
            json.dumps(state, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def retrieve_state(self) -> Dict[str, Any]:
        """Read the state from the JSON file or return an empty dict."""

        if not self.file_path.exists():
            return {}

        raw = self.file_path.read_text(encoding="utf-8")
        return json.loads(raw or "{}")
