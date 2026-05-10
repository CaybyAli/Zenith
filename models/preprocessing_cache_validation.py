from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PreprocessingCacheValidationResult:
    reusable: bool
    status: str
    severity: str

    cache_key: str | None = None
    expected_cache_key: str | None = None
    manifest_path: str | None = None
    source_path: str | None = None

    missing_paths: list[str] = field(default_factory=list)
    existing_paths: list[str] = field(default_factory=list)

    missing_targets: list[str] = field(default_factory=list)
    ready_targets: list[str] = field(default_factory=list)

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    recommendation: str = "rebuild"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reusable": self.reusable,
            "status": self.status,
            "severity": self.severity,
            "cache_key": self.cache_key,
            "expected_cache_key": self.expected_cache_key,
            "manifest_path": self.manifest_path,
            "source_path": self.source_path,
            "missing_paths": list(self.missing_paths),
            "existing_paths": list(self.existing_paths),
            "missing_targets": list(self.missing_targets),
            "ready_targets": list(self.ready_targets),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PreprocessingCacheValidationResult":
        return cls(
            reusable=bool(data.get("reusable", False)),
            status=str(data.get("status", "invalid")),
            severity=str(data.get("severity", "error")),
            cache_key=data.get("cache_key"),
            expected_cache_key=data.get("expected_cache_key"),
            manifest_path=data.get("manifest_path"),
            source_path=data.get("source_path"),
            missing_paths=list(data.get("missing_paths") or []),
            existing_paths=list(data.get("existing_paths") or []),
            missing_targets=list(data.get("missing_targets") or []),
            ready_targets=list(data.get("ready_targets") or []),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(data.get("recommendation", "rebuild")),
            details=dict(data.get("details") or {}),
        )
