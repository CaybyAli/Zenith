from __future__ import annotations

import json
import os
import shutil
from typing import Any

from storage.base_storage_provider import BaseStorageProvider


class LocalStorageProvider(BaseStorageProvider):
    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def ensure_dir(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    def list_dir(self, path: str) -> list[str]:
        return list(os.listdir(path))

    def is_dir(self, path: str) -> bool:
        return os.path.isdir(path)

    def read_json(self, path: str) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_json(self, path: str, data: Any, *, indent: int = 4) -> None:
        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

    def copy_file(self, source_path: str, target_path: str) -> None:
        parent_dir = os.path.dirname(target_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        shutil.copy(source_path, target_path)

    def join(self, *parts: str) -> str:
        return os.path.join(*parts)

    def abspath(self, path: str) -> str:
        return os.path.abspath(path)