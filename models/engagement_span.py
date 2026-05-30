from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


G7A_KEEP_RECOMMENDATIONS = (
    "keep_active",
    "trimmable_low_engagement",
    "frozen_or_paused",
)


@dataclass
class EngagementSpan:
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    keep_recommendation: str
    confidence: float
    reasons: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    source_g6_state_counts: Dict[str, int] = field(default_factory=dict)
    parent_active_context: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_seconds": round(float(self.start_seconds), 3),
            "end_seconds": round(float(self.end_seconds), 3),
            "duration_seconds": round(float(self.duration_seconds), 3),
            "state": self.keep_recommendation,
            "keep_recommendation": self.keep_recommendation,
            "confidence": round(float(self.confidence), 4),
            "reasons": list(self.reasons),
            "evidence": dict(self.evidence),
            "source_g6_state_counts": dict(self.source_g6_state_counts),
            "parent_active_context": dict(self.parent_active_context),
            "warnings": list(self.warnings),
        }


@dataclass
class ActivePlayEngagementResult:
    video_path: str
    analyzed_duration_seconds: float
    window_seconds: float
    thresholds: Dict[str, Any]
    active_contexts: List[Dict[str, float]]
    spans: List[EngagementSpan]
    ratios: Dict[str, float]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_path": self.video_path,
            "analyzed_duration_seconds": round(float(self.analyzed_duration_seconds), 3),
            "window_seconds": round(float(self.window_seconds), 3),
            "thresholds": dict(self.thresholds),
            "active_contexts": list(self.active_contexts),
            "spans": [span.to_dict() for span in self.spans],
            "ratios": dict(self.ratios),
            "warnings": list(self.warnings),
        }
