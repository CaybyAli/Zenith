from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shared.role_enums import RoleType


def _normalize_role(value: Any) -> RoleType:
    if isinstance(value, RoleType):
        return value

    try:
        return RoleType(str(value).strip().lower())
    except ValueError as exc:
        raise RuntimeError(f"Invalid role type: {value}") from exc


@dataclass(slots=True, frozen=True)
class ActorContext:
    actor_id: str
    role: RoleType
    workspace_id: str | None = None
    display_name: str | None = None
    is_remote: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "role": self.role.value,
            "workspace_id": self.workspace_id,
            "display_name": self.display_name,
            "is_remote": self.is_remote,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActorContext":
        return cls(
            actor_id=str(data.get("actor_id") or "").strip(),
            role=_normalize_role(data.get("role")),
            workspace_id=(
                str(data.get("workspace_id")).strip()
                if data.get("workspace_id") is not None
                else None
            ),
            display_name=(
                str(data.get("display_name")).strip()
                if data.get("display_name") is not None
                else None
            ),
            is_remote=bool(data.get("is_remote", False)),
        )