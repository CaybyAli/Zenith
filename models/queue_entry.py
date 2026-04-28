from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from shared.opportunity_enums import OpportunityLevel
from shared.opportunity_review_enums import OpportunityReviewStatus
from shared.queue_enums import QueueState
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


def _normalize_queue_state(value: Any) -> QueueState:
    cleaned = _clean_text(value, QueueState.BLOCKED.value).lower()

    for item in QueueState:
        if item.value == cleaned:
            return item

    return QueueState.BLOCKED


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
class QueueEntry:
    queue_entry_id: str
    dedupe_key: str

    source_review_view_id: str
    source_opportunity_id: str
    source_signal_id: str

    topic_label: str
    platform: str
    channel_type: str
    channel_group: str
    content_kind: str

    queue_state: QueueState
    opportunity_score: float
    opportunity_level: OpportunityLevel
    lifespan_class: LifespanClass
    review_status: OpportunityReviewStatus

    review_summary: str | None = None
    block_reason: str | None = None

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["queue_state"] = self.queue_state.value
        data["opportunity_level"] = self.opportunity_level.value
        data["lifespan_class"] = self.lifespan_class.value
        data["review_status"] = self.review_status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueueEntry":
        return cls(
            queue_entry_id=_clean_text(data.get("queue_entry_id")) or f"queue_{uuid4().hex[:12]}",
            dedupe_key=_clean_text(data.get("dedupe_key"), "missing_dedupe_key"),
            source_review_view_id=_clean_text(data.get("source_review_view_id"), "unknown_review"),
            source_opportunity_id=_clean_text(data.get("source_opportunity_id"), "unknown_opportunity"),
            source_signal_id=_clean_text(data.get("source_signal_id"), "unknown_signal"),
            topic_label=_clean_text(data.get("topic_label"), "untitled_topic"),
            platform=_clean_text(data.get("platform"), "unknown"),
            channel_type=_clean_text(data.get("channel_type"), "unknown_channel"),
            channel_group=_clean_text(data.get("channel_group"), "unknown_group"),
            content_kind=_clean_text(data.get("content_kind"), "longform"),
            queue_state=_normalize_queue_state(data.get("queue_state")),
            opportunity_score=round(
                _clamp_float(data.get("opportunity_score", 0.0), minimum=0.0, maximum=100.0),
                2,
            ),
            opportunity_level=_normalize_opportunity_level(data.get("opportunity_level")),
            lifespan_class=_normalize_lifespan_class(data.get("lifespan_class")),
            review_status=_normalize_review_status(data.get("review_status")),
            review_summary=_clean_text(data.get("review_summary")) or None,
            block_reason=_clean_text(data.get("block_reason")) or None,
            created_at=_clean_text(data.get("created_at")) or utc_now_iso(),
            updated_at=_clean_text(data.get("updated_at")) or utc_now_iso(),
        )