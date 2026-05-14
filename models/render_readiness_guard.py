from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


STATUS_READY = "render_readiness_ready"
STATUS_READY_WITH_WARNINGS = "render_readiness_ready_with_warnings"
STATUS_BLOCKED = "render_readiness_blocked"
STATUS_FAILED = "render_readiness_failed"

CHECK_STATUS_PASSED = "passed"
CHECK_STATUS_WARNING = "warning"
CHECK_STATUS_BLOCKED = "blocked"
CHECK_STATUS_FAILED = "failed"

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_BLOCKING = "blocking"
SEVERITY_FAILED = "failed"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class RenderReadinessCheck:
    check_id: str
    check_name: str
    category: str
    status: str
    severity: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    blocking: bool = False
    review_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RenderReadinessReport:
    report_id: str
    job_id: str
    status: str
    checks: list[RenderReadinessCheck] = field(default_factory=list)

    total_checks: int = 0
    passed_count: int = 0
    warning_count: int = 0
    blocking_count: int = 0

    review_required: bool = True
    ready_for_next_render_stage: bool = False
    can_start_render_pipeline: bool = False

    can_render: bool = False
    can_run_ffmpeg: bool = False
    can_execute_media_operations: bool = False
    can_apply_timeline: bool = False
    can_modify_media: bool = False

    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["checks"] = [check.to_dict() for check in self.checks]

        # 2B-45 darf niemals echte Render-/Medienrechte geben.
        data["can_render"] = False
        data["can_run_ffmpeg"] = False
        data["can_execute_media_operations"] = False
        data["can_apply_timeline"] = False
        data["can_modify_media"] = False

        return data


def build_report_from_checks(
    *,
    job_id: str,
    checks: list[RenderReadinessCheck],
    metadata: dict[str, Any] | None = None,
) -> RenderReadinessReport:
    passed_count = sum(1 for check in checks if check.status == CHECK_STATUS_PASSED)
    warning_count = sum(1 for check in checks if check.status == CHECK_STATUS_WARNING)
    blocking_count = sum(1 for check in checks if check.blocking)

    warnings = [
        check.message
        for check in checks
        if check.status == CHECK_STATUS_WARNING
    ]
    blocking_reasons = [
        check.message
        for check in checks
        if check.blocking
    ]

    hard_blocked = blocking_count > 0
    ready_for_next_stage = not hard_blocked
    has_warnings = warning_count > 0

    if hard_blocked:
        status = STATUS_BLOCKED
        recommendation = "Render readiness is blocked. Fix blocking reasons before the next render stage."
    elif has_warnings:
        status = STATUS_READY_WITH_WARNINGS
        recommendation = "Ready for the next render stage, but review warnings first."
    else:
        status = STATUS_READY
        recommendation = "Ready for the next render stage. 2B-45 still does not render."

    return RenderReadinessReport(
        report_id=f"render_readiness_{job_id}",
        job_id=job_id,
        status=status,
        checks=checks,
        total_checks=len(checks),
        passed_count=passed_count,
        warning_count=warning_count,
        blocking_count=blocking_count,
        review_required=has_warnings or hard_blocked,
        ready_for_next_render_stage=ready_for_next_stage,
        can_start_render_pipeline=ready_for_next_stage,
        can_render=False,
        can_run_ffmpeg=False,
        can_execute_media_operations=False,
        can_apply_timeline=False,
        can_modify_media=False,
        warnings=warnings,
        blocking_reasons=blocking_reasons,
        recommendation=recommendation,
        metadata=dict(metadata or {}),
    )
