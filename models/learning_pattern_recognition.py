from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class LearningFeedbackTrend:
    trend_id: str
    trend_type: str
    tag: str | None = None
    category: str | None = None
    occurrence_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    average_score: float | None = None
    confidence: float = 0.0
    severity: str = "info"
    first_seen_job_id: str | None = None
    latest_seen_job_id: str | None = None
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningFeedbackTrend":
        return cls(
            trend_id=str(data.get("trend_id") or ""),
            trend_type=str(data.get("trend_type") or "single_job_observation"),
            tag=data.get("tag"),
            category=data.get("category"),
            occurrence_count=int(data.get("occurrence_count", 0) or 0),
            positive_count=int(data.get("positive_count", 0) or 0),
            negative_count=int(data.get("negative_count", 0) or 0),
            neutral_count=int(data.get("neutral_count", 0) or 0),
            average_score=(
                float(data["average_score"])
                if data.get("average_score") is not None
                else None
            ),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            severity=str(data.get("severity") or "info"),
            first_seen_job_id=data.get("first_seen_job_id"),
            latest_seen_job_id=data.get("latest_seen_job_id"),
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class LearningPatternCluster:
    cluster_id: str
    cluster_type: str
    title: str
    description: str
    source_tags: list[str] = field(default_factory=list)
    source_categories: list[str] = field(default_factory=list)
    affected_parameters: list[str] = field(default_factory=list)
    occurrence_count: int = 0
    confidence: float = 0.0
    overfitting_risk: str = "medium"
    recommendation: str | None = None
    safe_to_use_for_future_proposal: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningPatternCluster":
        return cls(
            cluster_id=str(data.get("cluster_id") or ""),
            cluster_type=str(data.get("cluster_type") or "general_feedback_pattern"),
            title=str(data.get("title") or ""),
            description=str(data.get("description") or ""),
            source_tags=list(data.get("source_tags") or []),
            source_categories=list(data.get("source_categories") or []),
            affected_parameters=list(data.get("affected_parameters") or []),
            occurrence_count=int(data.get("occurrence_count", 0) or 0),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            overfitting_risk=str(data.get("overfitting_risk") or "medium"),
            recommendation=data.get("recommendation"),
            safe_to_use_for_future_proposal=bool(
                data.get("safe_to_use_for_future_proposal", False)
            ),
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class LearningPatternRecognitionReport:
    report_id: str
    job_id: str | None
    status: str
    profile: str | None = None
    source_feedback_status: str | None = None
    feedback_sample_count: int = 0
    trend_count: int = 0
    cluster_count: int = 0
    trends: list[LearningFeedbackTrend | dict[str, Any]] = field(default_factory=list)
    clusters: list[LearningPatternCluster | dict[str, Any]] = field(default_factory=list)
    top_positive_patterns: list[str] = field(default_factory=list)
    top_negative_patterns: list[str] = field(default_factory=list)
    repeated_issue_count: int = 0
    repeated_success_count: int = 0
    confidence: float = 0.0
    overfitting_risk: str = "medium"
    ready_for_future_style_dna_proposal: bool = False
    can_update_style_dna: bool = False
    can_write_style_dna: bool = False
    can_change_profile: bool = False
    can_change_cutting_rules: bool = False
    can_modify_timeline: bool = False
    can_trigger_render: bool = False
    can_publish: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["trends"] = [_as_payload(item) for item in self.trends]
        payload["clusters"] = [_as_payload(item) for item in self.clusters]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningPatternRecognitionReport":
        trends = [
            LearningFeedbackTrend.from_dict(item) if isinstance(item, dict) else item
            for item in list(data.get("trends") or [])
        ]
        clusters = [
            LearningPatternCluster.from_dict(item) if isinstance(item, dict) else item
            for item in list(data.get("clusters") or [])
        ]
        return cls(
            report_id=str(data.get("report_id") or ""),
            job_id=data.get("job_id"),
            status=str(data.get("status") or "learning_pattern_failed"),
            profile=data.get("profile"),
            source_feedback_status=data.get("source_feedback_status"),
            feedback_sample_count=int(data.get("feedback_sample_count", 0) or 0),
            trend_count=int(data.get("trend_count", 0) or 0),
            cluster_count=int(data.get("cluster_count", 0) or 0),
            trends=trends,
            clusters=clusters,
            top_positive_patterns=list(data.get("top_positive_patterns") or []),
            top_negative_patterns=list(data.get("top_negative_patterns") or []),
            repeated_issue_count=int(data.get("repeated_issue_count", 0) or 0),
            repeated_success_count=int(data.get("repeated_success_count", 0) or 0),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            overfitting_risk=str(data.get("overfitting_risk") or "medium"),
            ready_for_future_style_dna_proposal=bool(
                data.get("ready_for_future_style_dna_proposal", False)
            ),
            can_update_style_dna=False,
            can_write_style_dna=False,
            can_change_profile=False,
            can_change_cutting_rules=False,
            can_modify_timeline=False,
            can_trigger_render=False,
            can_publish=False,
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            recommendation=data.get("recommendation"),
            created_at=data.get("created_at"),
            metadata=dict(data.get("metadata") or {}),
        )


def _as_payload(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return dict(value)
    return dict(asdict(value))
