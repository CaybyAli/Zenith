from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


FEEDBACK_STATUS_WAITING = "feedback_intake_waiting_for_feedback"
FEEDBACK_STATUS_READY = "feedback_intake_ready"
FEEDBACK_STATUS_READY_WITH_WARNINGS = "feedback_intake_ready_with_warnings"
FEEDBACK_STATUS_BLOCKED = "feedback_intake_blocked"
FEEDBACK_STATUS_FAILED = "feedback_intake_failed"

SENTIMENT_POSITIVE = "positive"
SENTIMENT_NEGATIVE = "negative"
SENTIMENT_NEUTRAL = "neutral"

SEVERITY_INFO = "info"
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"

KNOWN_FEEDBACK_TAGS = {
    "cut_too_early",
    "cut_too_late",
    "segment_too_long",
    "segment_too_short",
    "missing_reaction",
    "wrong_hook",
    "bad_pacing",
    "sentence_cut_violation",
    "audio_too_loud",
    "audio_too_quiet",
    "boring_segment",
    "good_cut",
    "strong_hook",
    "good_reaction",
    "good_pacing",
    "wrong_censor",
    "good_censor",
    "render_quality_issue",
    "output_format_issue",
}

KNOWN_FEEDBACK_CATEGORIES = {
    "overall_quality",
    "hook_quality",
    "pacing_quality",
    "story_quality",
    "audio_quality",
    "visual_quality",
    "render_quality",
    "timeline",
    "cut",
    "segment",
    "reaction",
    "hook",
    "pacing",
    "story",
    "audio",
    "visual",
    "render",
    "format",
    "censor",
    "custom",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_score(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        score = round(float(value), 1)
    except (TypeError, ValueError):
        return None
    return score


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = normalize_text(item)
        if text:
            items.append(text)
    return items


def normalize_sentiment(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {SENTIMENT_POSITIVE, SENTIMENT_NEGATIVE, SENTIMENT_NEUTRAL}:
        return text
    return SENTIMENT_NEUTRAL


def normalize_severity(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {SEVERITY_INFO, SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL}:
        return text
    return SEVERITY_INFO


def normalize_timestamp(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


@dataclass
class FeedbackTimestampItem:
    item_id: str | None = None
    timestamp_seconds: float | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    category: str | None = None
    tag: str | None = None
    sentiment: str = SENTIMENT_NEUTRAL
    severity: str = SEVERITY_INFO
    comment: str | None = None
    linked_item_id: str | None = None
    linked_segment_id: str | None = None
    valid: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "FeedbackTimestampItem":
        data = dict(data or {})
        return cls(
            item_id=normalize_text(data.get("item_id")),
            timestamp_seconds=normalize_timestamp(data.get("timestamp_seconds")),
            start_seconds=normalize_timestamp(data.get("start_seconds")),
            end_seconds=normalize_timestamp(data.get("end_seconds")),
            category=normalize_text(data.get("category")),
            tag=normalize_text(data.get("tag")),
            sentiment=normalize_sentiment(data.get("sentiment")),
            severity=normalize_severity(data.get("severity")),
            comment=normalize_text(data.get("comment")),
            linked_item_id=normalize_text(data.get("linked_item_id")),
            linked_segment_id=normalize_text(data.get("linked_segment_id")),
            valid=bool(data.get("valid", True)),
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FeedbackSubmission:
    submission_id: str | None = None
    job_id: str | None = None
    submitted_by: str | None = None
    submitted_at: str | None = None
    video_score: float | None = None
    overall_quality_score: float | None = None
    hook_quality_score: float | None = None
    pacing_quality_score: float | None = None
    story_quality_score: float | None = None
    audio_quality_score: float | None = None
    visual_quality_score: float | None = None
    render_quality_score: float | None = None
    comment: str | None = None
    tags: list[str] = field(default_factory=list)
    timestamp_items: list[FeedbackTimestampItem] = field(default_factory=list)
    valid: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "FeedbackSubmission":
        data = dict(data or {})
        return cls(
            submission_id=normalize_text(data.get("submission_id")),
            job_id=normalize_text(data.get("job_id")),
            submitted_by=normalize_text(data.get("submitted_by")),
            submitted_at=normalize_text(data.get("submitted_at")),
            video_score=normalize_score(data.get("video_score")),
            overall_quality_score=normalize_score(data.get("overall_quality_score")),
            hook_quality_score=normalize_score(data.get("hook_quality_score")),
            pacing_quality_score=normalize_score(data.get("pacing_quality_score")),
            story_quality_score=normalize_score(data.get("story_quality_score")),
            audio_quality_score=normalize_score(data.get("audio_quality_score")),
            visual_quality_score=normalize_score(data.get("visual_quality_score")),
            render_quality_score=normalize_score(data.get("render_quality_score")),
            comment=normalize_text(data.get("comment")),
            tags=normalize_text_list(data.get("tags")),
            timestamp_items=[
                FeedbackTimestampItem.from_dict(item)
                for item in list(data.get("timestamp_items") or [])
                if isinstance(item, dict)
            ],
            valid=bool(data.get("valid", True)),
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp_items"] = [item.to_dict() for item in self.timestamp_items]
        return payload


@dataclass
class FeedbackIntakeReport:
    report_id: str | None = None
    job_id: str | None = None
    status: str = FEEDBACK_STATUS_WAITING
    submissions: list[FeedbackSubmission] = field(default_factory=list)
    submission_count: int = 0
    timestamp_feedback_count: int = 0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    neutral_feedback_count: int = 0
    average_video_score: float | None = None
    tags_summary: dict[str, int] = field(default_factory=dict)
    category_summary: dict[str, int] = field(default_factory=dict)
    review_required: bool = True
    ready_for_style_dna_update: bool = False
    can_update_style_dna: bool = False
    can_change_profile: bool = False
    can_change_cutting_rules: bool = False
    can_modify_timeline: bool = False
    can_trigger_render: bool = False
    can_publish: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "FeedbackIntakeReport":
        data = dict(data or {})
        return cls(
            report_id=normalize_text(data.get("report_id")),
            job_id=normalize_text(data.get("job_id")),
            status=normalize_text(data.get("status")) or FEEDBACK_STATUS_WAITING,
            submissions=[
                FeedbackSubmission.from_dict(item)
                for item in list(data.get("submissions") or [])
                if isinstance(item, dict)
            ],
            submission_count=int(data.get("submission_count", 0) or 0),
            timestamp_feedback_count=int(data.get("timestamp_feedback_count", 0) or 0),
            positive_feedback_count=int(data.get("positive_feedback_count", 0) or 0),
            negative_feedback_count=int(data.get("negative_feedback_count", 0) or 0),
            neutral_feedback_count=int(data.get("neutral_feedback_count", 0) or 0),
            average_video_score=normalize_score(data.get("average_video_score")),
            tags_summary=dict(data.get("tags_summary") or {}),
            category_summary=dict(data.get("category_summary") or {}),
            review_required=bool(data.get("review_required", True)),
            ready_for_style_dna_update=bool(data.get("ready_for_style_dna_update", False)),
            can_update_style_dna=False,
            can_change_profile=False,
            can_change_cutting_rules=False,
            can_modify_timeline=False,
            can_trigger_render=False,
            can_publish=False,
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            recommendation=normalize_text(data.get("recommendation")),
            created_at=normalize_text(data.get("created_at")) or utc_now_iso(),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["submissions"] = [submission.to_dict() for submission in self.submissions]
        payload["can_update_style_dna"] = False
        payload["can_change_profile"] = False
        payload["can_change_cutting_rules"] = False
        payload["can_modify_timeline"] = False
        payload["can_trigger_render"] = False
        payload["can_publish"] = False
        return payload
