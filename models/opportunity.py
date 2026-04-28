from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from shared.opportunity_enums import OpportunityLevel


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


def _clean_channel_scores(values: Any) -> dict[str, float]:
    if not isinstance(values, dict):
        return {}

    cleaned: dict[str, float] = {}
    for key, value in values.items():
        channel = _clean_text(key).lower()
        if not channel:
            continue
        cleaned[channel] = round(
            _clamp_float(value, minimum=0.0, maximum=100.0),
            2,
        )

    return cleaned


def _normalize_opportunity_level(value: Any) -> OpportunityLevel:
    cleaned = _clean_text(value, OpportunityLevel.LOW.value).lower()

    for item in OpportunityLevel:
        if item.value == cleaned:
            return item

    return OpportunityLevel.LOW


@dataclass(slots=True)
class Opportunity:
    opportunity_id: str
    signal_id: str
    qualification_id: str

    opportunity_score: float
    opportunity_level: OpportunityLevel
    primary_channel: str | None

    channel_scores: dict[str, float] = field(default_factory=dict)
    upside_factors: list[str] = field(default_factory=list)
    downside_factors: list[str] = field(default_factory=list)
    opportunity_reason: str | None = None

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["opportunity_level"] = self.opportunity_level.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Opportunity":
        return cls(
            opportunity_id=_clean_text(data.get("opportunity_id")) or f"opportunity_{uuid4().hex[:12]}",
            signal_id=_clean_text(data.get("signal_id"), "unknown_signal"),
            qualification_id=_clean_text(data.get("qualification_id"), "unknown_qualification"),
            opportunity_score=round(
                _clamp_float(data.get("opportunity_score", 0.0), minimum=0.0, maximum=100.0),
                2,
            ),
            opportunity_level=_normalize_opportunity_level(data.get("opportunity_level")),
            primary_channel=_clean_text(data.get("primary_channel")) or None,
            channel_scores=_clean_channel_scores(data.get("channel_scores")),
            upside_factors=_clean_list(data.get("upside_factors")),
            downside_factors=_clean_list(data.get("downside_factors")),
            opportunity_reason=_clean_text(data.get("opportunity_reason")) or None,
            created_at=_clean_text(data.get("created_at")) or utc_now_iso(),
            updated_at=_clean_text(data.get("updated_at")) or utc_now_iso(),
        )