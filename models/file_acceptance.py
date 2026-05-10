from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FileAcceptanceResult:
    accepted: bool
    status: str
    severity: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    file_path: str | None = None
    extension: str | None = None
    profile_id: str | None = None
    recommendation: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "severity": self.severity,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "file_path": self.file_path,
            "extension": self.extension,
            "profile_id": self.profile_id,
            "recommendation": self.recommendation,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileAcceptanceResult":
        return cls(
            accepted=bool(data.get("accepted", False)),
            status=str(data.get("status", "rejected")),
            severity=str(data.get("severity", "error")),
            reasons=list(data.get("reasons") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            file_path=data.get("file_path"),
            extension=data.get("extension"),
            profile_id=data.get("profile_id"),
            recommendation=data.get("recommendation"),
            details=dict(data.get("details") or {}),
        )
