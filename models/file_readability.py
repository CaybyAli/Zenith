from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FileReadabilityResult:
    readable: bool
    status: str
    severity: str
    file_path: str
    checked_seconds: float = 0.0
    ffmpeg_returncode: int | None = None
    stdout_tail: str | None = None
    stderr_tail: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "manual_review"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "readable": self.readable,
            "status": self.status,
            "severity": self.severity,
            "file_path": self.file_path,
            "checked_seconds": self.checked_seconds,
            "ffmpeg_returncode": self.ffmpeg_returncode,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileReadabilityResult":
        return cls(
            readable=bool(data.get("readable", False)),
            status=str(data.get("status", "failed")),
            severity=str(data.get("severity", "error")),
            file_path=str(data.get("file_path", "")),
            checked_seconds=float(data.get("checked_seconds", 0.0) or 0.0),
            ffmpeg_returncode=data.get("ffmpeg_returncode"),
            stdout_tail=data.get("stdout_tail"),
            stderr_tail=data.get("stderr_tail"),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(data.get("recommendation", "manual_review")),
            details=dict(data.get("details") or {}),
        )
