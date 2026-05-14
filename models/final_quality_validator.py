from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


FINAL_QUALITY_READY = "final_quality_ready"
FINAL_QUALITY_READY_WITH_WARNINGS = "final_quality_ready_with_warnings"
FINAL_QUALITY_BLOCKED = "final_quality_blocked"
FINAL_QUALITY_NO_TIMELINE_ITEMS = "no_timeline_items"
FINAL_QUALITY_FAILED = "failed"

CHECK_PASSED = "passed"
CHECK_WARNING = "warning"
CHECK_BLOCKED = "blocked"
CHECK_SKIPPED = "skipped"

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_BLOCKING = "blocking"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FinalQualityCheck:
    check_id: str
    category: str
    check_name: str
    status: str
    severity: str
    score: float
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    review_required: bool = False
    blocking: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FinalQualitySuggestion:
    suggestion_id: str
    suggestion_type: str
    category: str
    severity: str
    reason: str
    review_required: bool = True
    can_auto_apply: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["can_auto_apply"] = False
        return data


@dataclass
class FinalQualityValidationReport:
    report_id: str
    job_id: str
    status: str
    checks: List[FinalQualityCheck] = field(default_factory=list)
    suggestions: List[FinalQualitySuggestion] = field(default_factory=list)

    audio_score: float = 0.0
    video_score: float = 0.0
    story_score: float = 0.0
    pacing_score: float = 0.0
    safety_score: float = 1.0
    overall_quality_score: float = 0.0

    total_checks: int = 0
    passed_count: int = 0
    warning_count: int = 0
    blocking_count: int = 0

    review_required: bool = True

    can_apply_fixes: bool = False
    can_render: bool = False
    can_execute_timeline: bool = False
    can_reorder_timeline: bool = False
    can_trim: bool = False
    can_extend: bool = False
    can_insert_effects: bool = False

    warnings: List[str] = field(default_factory=list)
    blocking_reasons: List[str] = field(default_factory=list)
    recommendation: str = "review_final_quality"

    created_at: str = field(default_factory=utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def enforce_review_only_safety(self) -> None:
        self.review_required = True
        self.can_apply_fixes = False
        self.can_render = False
        self.can_execute_timeline = False
        self.can_reorder_timeline = False
        self.can_trim = False
        self.can_extend = False
        self.can_insert_effects = False

    def recalculate_counts(self) -> None:
        self.total_checks = len(self.checks)
        self.passed_count = len([check for check in self.checks if check.status == CHECK_PASSED])
        self.warning_count = len([check for check in self.checks if check.status == CHECK_WARNING])
        self.blocking_count = len([check for check in self.checks if check.status == CHECK_BLOCKED])

        self.warnings = [
            check.message
            for check in self.checks
            if check.status == CHECK_WARNING
        ]
        self.blocking_reasons = [
            check.message
            for check in self.checks
            if check.status == CHECK_BLOCKED or check.blocking
        ]

        if self.blocking_count > 0:
            self.status = FINAL_QUALITY_BLOCKED
        elif self.warning_count > 0:
            self.status = FINAL_QUALITY_READY_WITH_WARNINGS
        elif self.total_checks == 0:
            self.status = FINAL_QUALITY_NO_TIMELINE_ITEMS
        else:
            self.status = FINAL_QUALITY_READY

        self.enforce_review_only_safety()

    def to_dict(self) -> Dict[str, Any]:
        self.recalculate_counts()
        return {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "status": self.status,
            "checks": [check.to_dict() for check in self.checks],
            "suggestions": [suggestion.to_dict() for suggestion in self.suggestions],
            "audio_score": self.audio_score,
            "video_score": self.video_score,
            "story_score": self.story_score,
            "pacing_score": self.pacing_score,
            "safety_score": self.safety_score,
            "overall_quality_score": self.overall_quality_score,
            "total_checks": self.total_checks,
            "passed_count": self.passed_count,
            "warning_count": self.warning_count,
            "blocking_count": self.blocking_count,
            "review_required": True,
            "can_apply_fixes": False,
            "can_render": False,
            "can_execute_timeline": False,
            "can_reorder_timeline": False,
            "can_trim": False,
            "can_extend": False,
            "can_insert_effects": False,
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
            "recommendation": self.recommendation,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


def final_quality_report_from_dict(data: Optional[Dict[str, Any]]) -> Optional[FinalQualityValidationReport]:
    if not data:
        return None

    checks = [
        FinalQualityCheck(**check)
        for check in data.get("checks", [])
    ]
    suggestions = [
        FinalQualitySuggestion(**suggestion)
        for suggestion in data.get("suggestions", [])
    ]

    report = FinalQualityValidationReport(
        report_id=data.get("report_id", "final_quality_unknown"),
        job_id=data.get("job_id", "unknown"),
        status=data.get("status", FINAL_QUALITY_READY_WITH_WARNINGS),
        checks=checks,
        suggestions=suggestions,
        audio_score=float(data.get("audio_score", 0.0)),
        video_score=float(data.get("video_score", 0.0)),
        story_score=float(data.get("story_score", 0.0)),
        pacing_score=float(data.get("pacing_score", 0.0)),
        safety_score=float(data.get("safety_score", 1.0)),
        overall_quality_score=float(data.get("overall_quality_score", 0.0)),
        warnings=list(data.get("warnings", [])),
        blocking_reasons=list(data.get("blocking_reasons", [])),
        recommendation=data.get("recommendation", "review_final_quality"),
        created_at=data.get("created_at", utc_now_iso()),
        metadata=dict(data.get("metadata", {})),
    )
    report.enforce_review_only_safety()
    report.recalculate_counts()
    return report
