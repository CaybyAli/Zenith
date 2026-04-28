from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseStorageProvider(ABC):
    @abstractmethod
    def exists(self, path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def ensure_dir(self, path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_dir(self, path: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def is_dir(self, path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def read_json(self, path: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def write_json(self, path: str, data: Any, *, indent: int = 4) -> None:
        raise NotImplementedError

    @abstractmethod
    def copy_file(self, source_path: str, target_path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def join(self, *parts: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def abspath(self, path: str) -> str:
        raise NotImplementedError