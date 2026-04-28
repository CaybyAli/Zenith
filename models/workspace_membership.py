from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.role_enums import RoleType


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_role(value: Any) -> RoleType:
    if isinstance(value, RoleType):
        return value

    try:
        return RoleType(str(value).strip().lower())
    except ValueError as exc:
        raise RuntimeError(f"Invalid role type: {value}") from exc


@dataclass(slots=True)
class WorkspaceMembership:
    actor_id: str
    workspace_id: str
    role: RoleType
    enabled: bool = True
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "workspace_id": self.workspace_id,
            "role": self.role.value,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkspaceMembership":
        return cls(
            actor_id=str(data.get("actor_id") or "").strip(),
            workspace_id=str(data.get("workspace_id") or "").strip(),
            role=_normalize_role(data.get("role")),
            enabled=bool(data.get("enabled", True)),
            created_at=str(data.get("created_at") or utc_now_iso()),
            updated_at=str(data.get("updated_at") or utc_now_iso()),
        )