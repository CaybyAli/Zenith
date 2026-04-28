from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from shared.opportunity_enums import OpportunityLevel
from shared.opportunity_review_enums import OpportunityReviewStatus
from shared.trend_qualification_enums import LifespanClass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _clamp_float(value: float | int | str | None, *, minimum: float, maximum: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = minimum

    return max(minimum, min(maximum, numeric))


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []

    cleaned: list[str] = []
    for item in values:
        text = _clean_text(item)
        if text:
            cleaned.append(text)

    return cleaned


def _normalize_opportunity_level(value: Any) -> OpportunityLevel:
    cleaned = _clean_text(value, OpportunityLevel.LOW.value).lower()

    for item in OpportunityLevel:
        if item.value == cleaned:
            return item

    return OpportunityLevel.LOW


def _normalize_lifespan_class(value: Any) -> LifespanClass:
    cleaned = _clean_text(value, LifespanClass.SHORT.value).lower()

    for item in LifespanClass:
        if item.value == cleaned:
            return item

    return LifespanClass.SHORT


def _normalize_review_status(value: Any) -> OpportunityReviewStatus:
    cleaned = _clean_text(value, OpportunityReviewStatus.PENDING.value).lower()

    for item in OpportunityReviewStatus:
        if item.value == cleaned:
            return item

    return OpportunityReviewStatus.PENDING


@dataclass(slots=True)
class OpportunityReviewView:
    review_view_id: str
    signal_id: str
    qualification_id: str
    opportunity_id: str

    topic_label: str
    platform: str
    primary_channel: str | None

    opportunity_score: float
    opportunity_level: OpportunityLevel

    upside_preview: list[str] = field(default_factory=list)
    downside_preview: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    lifespan_class: LifespanClass = LifespanClass.SHORT

    review_status: OpportunityReviewStatus = OpportunityReviewStatus.PENDING
    review_summary: str | None = None

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["opportunity_level"] = self.opportunity_level.value
        data["lifespan_class"] = self.lifespan_class.value
        data["review_status"] = self.review_status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpportunityReviewView":
        return cls(
            review_view_id=_clean_text(data.get("review_view_id")) or f"review_{uuid4().hex[:12]}",
            signal_id=_clean_text(data.get("signal_id"), "unknown_signal"),
            qualification_id=_clean_text(data.get("qualification_id"), "unknown_qualification"),
            opportunity_id=_clean_text(data.get("opportunity_id"), "unknown_opportunity"),
            topic_label=_clean_text(data.get("topic_label"), "untitled_topic"),
            platform=_clean_text(data.get("platform"), "unknown"),
            primary_channel=_clean_text(data.get("primary_channel")) or None,
            opportunity_score=round(
                _clamp_float(data.get("opportunity_score", 0.0), minimum=0.0, maximum=100.0),
                2,
            ),
            opportunity_level=_normalize_opportunity_level(data.get("opportunity_level")),
            upside_preview=_clean_list(data.get("upside_preview")),
            downside_preview=_clean_list(data.get("downside_preview")),
            risk_flags=_clean_list(data.get("risk_flags")),
            lifespan_class=_normalize_lifespan_class(data.get("lifespan_class")),
            review_status=_normalize_review_status(data.get("review_status")),
            review_summary=_clean_text(data.get("review_summary")) or None,
            created_at=_clean_text(data.get("created_at")) or utc_now_iso(),
            updated_at=_clean_text(data.get("updated_at")) or utc_now_iso(),
        )