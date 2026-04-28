from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.enums import PlatformType


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class PublishGuardResult:
    job_id: str
    variant_id: str | None
    target_platform: PlatformType
    guard_status: str

    risk_flags: list[str] = field(default_factory=list)
    guard_reason: str = ""
    matched_reference_ids: list[str] = field(default_factory=list)

    similarity_score: float | None = None
    requires_manual_review: bool = False
    guard_snapshot: dict[str, Any] = field(default_factory=dict)
    guard_notes: str | None = None

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "variant_id": self.variant_id,
            "target_platform": self.target_platform.value,
            "guard_status": self.guard_status,
            "risk_flags": list(self.risk_flags),
            "guard_reason": self.guard_reason,
            "matched_reference_ids": list(self.matched_reference_ids),
            "similarity_score": self.similarity_score,
            "requires_manual_review": self.requires_manual_review,
            "guard_snapshot": dict(self.guard_snapshot),
            "guard_notes": self.guard_notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PublishGuardResult":
        return cls(
            job_id=str(data.get("job_id")),
            variant_id=data.get("variant_id"),
            target_platform=PlatformType(data.get("target_platform", "youtube")),
            guard_status=str(data.get("guard_status", "allow")),
            risk_flags=list(data.get("risk_flags", [])),
            guard_reason=str(data.get("guard_reason", "")),
            matched_reference_ids=list(data.get("matched_reference_ids", [])),
            similarity_score=(
                float(data["similarity_score"])
                if data.get("similarity_score") is not None
                else None
            ),
            requires_manual_review=bool(data.get("requires_manual_review", False)),
            guard_snapshot=dict(data.get("guard_snapshot", {})),
            guard_notes=data.get("guard_notes"),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
        )