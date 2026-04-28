from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from shared.trend_qualification_enums import ContentShape, DecisionHint, LifespanClass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []

    cleaned: list[str] = []
    for item in values:
        text = _clean_text(item)
        if text:
            cleaned.append(text)

    return cleaned


def _normalize_content_shape(value: Any) -> ContentShape:
    cleaned = _clean_text(value, ContentShape.UNKNOWN.value).lower()

    for item in ContentShape:
        if item.value == cleaned:
            return item

    return ContentShape.UNKNOWN


def _normalize_lifespan_class(value: Any) -> LifespanClass:
    cleaned = _clean_text(value, LifespanClass.SHORT.value).lower()

    for item in LifespanClass:
        if item.value == cleaned:
            return item

    return LifespanClass.SHORT


def _normalize_decision_hint(value: Any) -> DecisionHint:
    cleaned = _clean_text(value, DecisionHint.WATCH.value).lower()

    for item in DecisionHint:
        if item.value == cleaned:
            return item

    return DecisionHint.WATCH


@dataclass(slots=True)
class TrendQualification:
    qualification_id: str
    signal_id: str

    fit_main: bool
    fit_uncut: bool
    fit_faceless: bool

    content_shape: ContentShape
    lifespan_class: LifespanClass

    risk_flags: list[str] = field(default_factory=list)
    decision_hint: DecisionHint = DecisionHint.WATCH
    qualification_notes: list[str] = field(default_factory=list)

    transcript_hints: list[str] = field(default_factory=list)
    multi_track_hints: list[str] = field(default_factory=list)
    metadata_hints: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["content_shape"] = self.content_shape.value
        data["lifespan_class"] = self.lifespan_class.value
        data["decision_hint"] = self.decision_hint.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrendQualification":
        return cls(
            qualification_id=_clean_text(data.get("qualification_id")) or f"qualification_{uuid4().hex[:12]}",
            signal_id=_clean_text(data.get("signal_id"), "unknown_signal"),
            fit_main=bool(data.get("fit_main", False)),
            fit_uncut=bool(data.get("fit_uncut", False)),
            fit_faceless=bool(data.get("fit_faceless", False)),
            content_shape=_normalize_content_shape(data.get("content_shape")),
            lifespan_class=_normalize_lifespan_class(data.get("lifespan_class")),
            risk_flags=_clean_list(data.get("risk_flags")),
            decision_hint=_normalize_decision_hint(data.get("decision_hint")),
            qualification_notes=_clean_list(data.get("qualification_notes")),
            transcript_hints=_clean_list(data.get("transcript_hints")),
            multi_track_hints=_clean_list(data.get("multi_track_hints")),
            metadata_hints=dict(data.get("metadata_hints", {})),
            created_at=_clean_text(data.get("created_at")) or utc_now_iso(),
            updated_at=_clean_text(data.get("updated_at")) or utc_now_iso(),
        )