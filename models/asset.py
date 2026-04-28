from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.enums import AssetStatus, AssetType


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Asset:
    asset_id: str
    job_id: str
    asset_type: AssetType
    path: str
    status: AssetStatus
    created_by_module: str
    created_at: str

    @classmethod
    def create(
        cls,
        *,
        asset_id: str,
        job_id: str,
        asset_type: AssetType,
        path: str,
        created_by_module: str,
        status: AssetStatus = AssetStatus.REGISTERED,
    ) -> "Asset":
        return cls(
            asset_id=asset_id,
            job_id=job_id,
            asset_type=asset_type,
            path=str(Path(path)),
            status=status,
            created_by_module=created_by_module,
            created_at=utc_now_iso(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Asset":
        return cls(
            asset_id=data["asset_id"],
            job_id=data["job_id"],
            asset_type=AssetType(data["asset_type"]),
            path=data["path"],
            status=AssetStatus(data["status"]),
            created_by_module=data["created_by_module"],
            created_at=data["created_at"],
        )