from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TrendSourceConnector(ABC):
    connector_name: str = "unknown_connector"

    @abstractmethod
    def fetch_items(self) -> list[dict[str, Any]]:
        raise NotImplementedError