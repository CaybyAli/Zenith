from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from shared.trend_enums import TrendPlatform, TrendSourceType


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


def _normalize_platform(value: Any) -> TrendPlatform:
    cleaned = _clean_text(value, "unknown").lower()

    alias_map = {
        "youtube": TrendPlatform.YOUTUBE,
        "yt": TrendPlatform.YOUTUBE,
        "youtube_shorts": TrendPlatform.YOUTUBE,
        "tiktok": TrendPlatform.TIKTOK,
        "tik tok": TrendPlatform.TIKTOK,
        "tik_tok": TrendPlatform.TIKTOK,
        "instagram": TrendPlatform.INSTAGRAM,
        "insta": TrendPlatform.INSTAGRAM,
        "reels": TrendPlatform.INSTAGRAM,
        "x": TrendPlatform.X,
        "twitter": TrendPlatform.X,
        "reddit": TrendPlatform.REDDIT,
        "web": TrendPlatform.WEB,
        "website": TrendPlatform.WEB,
        "blog": TrendPlatform.WEB,
        "news": TrendPlatform.WEB,
        "unknown": TrendPlatform.UNKNOWN,
    }

    return alias_map.get(cleaned, TrendPlatform.UNKNOWN)


def _normalize_source_type(value: Any) -> TrendSourceType:
    cleaned = _clean_text(value, "manual").lower()

    for source_type in TrendSourceType:
        if source_type.value == cleaned:
            return source_type

    return TrendSourceType.MANUAL


def _parse_iso_or_now(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return utc_now_iso()

    try:
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return utc_now_iso()


def _hours_between(older_iso: str, newer_iso: str) -> float:
    older = datetime.fromisoformat(older_iso.replace("Z", "+00:00"))
    newer = datetime.fromisoformat(newer_iso.replace("Z", "+00:00"))
    delta = newer - older
    hours = delta.total_seconds() / 3600
    return round(max(0.0, hours), 2)


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []

    cleaned: list[str] = []
    for item in values:
        text = _clean_text(item)
        if text:
            cleaned.append(text)

    return cleaned


@dataclass(slots=True)
class TrendSignal:
    signal_id: str
    source_id: str
    source_type: TrendSourceType
    platform: TrendPlatform

    topic: str
    raw_label: str
    normalized_label: str

    captured_at: str
    observed_at: str
    normalized_at: str

    freshness_hours: float
    half_life_hours: float
    signal_strength: float
    competition_density: float
    confidence: float

    language: str | None = None
    region: str | None = None
    channel_targets: list[str] = field(default_factory=list)

    raw_payload: dict[str, Any] = field(default_factory=dict)
    normalized_payload: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_type"] = self.source_type.value
        data["platform"] = self.platform.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrendSignal":
        observed_at = _parse_iso_or_now(data.get("observed_at"))
        normalized_at = _parse_iso_or_now(data.get("normalized_at"))
        captured_at = _parse_iso_or_now(data.get("captured_at"))

        freshness_hours = data.get("freshness_hours")
        if freshness_hours is None:
            freshness_hours = _hours_between(observed_at, normalized_at)

        return cls(
            signal_id=_clean_text(data.get("signal_id")) or f"signal_{uuid4().hex[:12]}",
            source_id=_clean_text(data.get("source_id"), "unknown_source"),
            source_type=_normalize_source_type(data.get("source_type")),
            platform=_normalize_platform(data.get("platform")),
            topic=_clean_text(data.get("topic"), "untitled_trend"),
            raw_label=_clean_text(data.get("raw_label"), "untitled_trend"),
            normalized_label=_clean_text(data.get("normalized_label"), "untitled_trend"),
            captured_at=captured_at,
            observed_at=observed_at,
            normalized_at=normalized_at,
            freshness_hours=round(
                _clamp_float(freshness_hours, minimum=0.0, maximum=100000.0),
                2,
            ),
            half_life_hours=round(
                _clamp_float(data.get("half_life_hours", 24.0), minimum=1.0, maximum=720.0),
                2,
            ),
            signal_strength=round(
                _clamp_float(data.get("signal_strength", 0.5), minimum=0.0, maximum=1.0),
                4,
            ),
            competition_density=round(
                _clamp_float(data.get("competition_density", 0.5), minimum=0.0, maximum=1.0),
                4,
            ),
            confidence=round(
                _clamp_float(data.get("confidence", 0.5), minimum=0.0, maximum=1.0),
                4,
            ),
            language=_clean_text(data.get("language")) or None,
            region=_clean_text(data.get("region")) or None,
            channel_targets=_clean_list(data.get("channel_targets")),
            raw_payload=dict(data.get("raw_payload", {})),
            normalized_payload=dict(data.get("normalized_payload", {})),
            notes=_clean_list(data.get("notes")),
            created_at=_clean_text(data.get("created_at")) or utc_now_iso(),
            updated_at=_clean_text(data.get("updated_at")) or utc_now_iso(),
        )