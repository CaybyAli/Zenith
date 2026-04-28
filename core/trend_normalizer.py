from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models.trend_signal import TrendSignal
from models.trend_source import TrendSource
from shared.trend_enums import TrendPlatform


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


class TrendNormalizer:
    def normalize_source(self, source: TrendSource | dict[str, Any]) -> TrendSource:
        if isinstance(source, TrendSource):
            return TrendSource.from_dict(source.to_dict())

        return TrendSource.from_dict(source)

    def normalize_signal(
        self,
        *,
        source: TrendSource,
        raw_signal: dict[str, Any],
    ) -> TrendSignal:
        raw_copy = dict(raw_signal)

        captured_at = _parse_iso_or_now(raw_signal.get("captured_at"))
        observed_at = _parse_iso_or_now(raw_signal.get("observed_at"))
        normalized_at = utc_now_iso()

        raw_label = self._derive_raw_label(raw_signal)
        topic = self._derive_topic(raw_signal, raw_label)
        normalized_label = self._normalize_label(topic)

        platform_value = _clean_text(raw_signal.get("platform")).lower()
        if not platform_value:
            platform = source.platform
        else:
            platform = self._normalize_platform(platform_value)

        half_life_hours = round(
            _clamp_float(
                raw_signal.get("half_life_hours", source.default_half_life_hours),
                minimum=1.0,
                maximum=720.0,
            ),
            2,
        )

        signal_strength = round(
            _clamp_float(raw_signal.get("signal_strength", 0.5), minimum=0.0, maximum=1.0),
            4,
        )
        competition_density = round(
            _clamp_float(raw_signal.get("competition_density", 0.5), minimum=0.0, maximum=1.0),
            4,
        )
        confidence = round(
            _clamp_float(
                raw_signal.get("confidence", source.reliability_weight),
                minimum=0.0,
                maximum=1.0,
            ),
            4,
        )

        freshness_hours = _hours_between(observed_at, normalized_at)

        notes: list[str] = []
        if not raw_signal.get("observed_at"):
            notes.append("observed_at_missing_used_current_time")
        if not raw_signal.get("captured_at"):
            notes.append("captured_at_missing_used_current_time")
        if platform == TrendPlatform.UNKNOWN:
            notes.append("platform_unknown")

        normalized_payload = {
            "topic": topic,
            "normalized_label": normalized_label,
            "platform": platform.value,
            "source_id": source.source_id,
            "source_type": source.source_type.value,
            "freshness_hours": freshness_hours,
            "half_life_hours": half_life_hours,
            "signal_strength": signal_strength,
            "competition_density": competition_density,
            "confidence": confidence,
            "channel_targets": self._normalize_channel_targets(raw_signal.get("channel_targets")),
        }

        return TrendSignal.from_dict(
            {
                "source_id": source.source_id,
                "source_type": source.source_type.value,
                "platform": platform.value,
                "topic": topic,
                "raw_label": raw_label,
                "normalized_label": normalized_label,
                "captured_at": captured_at,
                "observed_at": observed_at,
                "normalized_at": normalized_at,
                "freshness_hours": freshness_hours,
                "half_life_hours": half_life_hours,
                "signal_strength": signal_strength,
                "competition_density": competition_density,
                "confidence": confidence,
                "language": _clean_text(raw_signal.get("language")) or None,
                "region": _clean_text(raw_signal.get("region")) or None,
                "channel_targets": self._normalize_channel_targets(raw_signal.get("channel_targets")),
                "raw_payload": raw_copy,
                "normalized_payload": normalized_payload,
                "notes": notes,
            }
        )

    def _derive_raw_label(self, raw_signal: dict[str, Any]) -> str:
        candidates = [
            raw_signal.get("raw_label"),
            raw_signal.get("label"),
            raw_signal.get("title"),
            raw_signal.get("topic"),
            raw_signal.get("query"),
            raw_signal.get("text"),
        ]

        for candidate in candidates:
            cleaned = _clean_text(candidate)
            if cleaned:
                return cleaned

        return "untitled_trend"

    def _derive_topic(self, raw_signal: dict[str, Any], fallback: str) -> str:
        candidates = [
            raw_signal.get("topic"),
            raw_signal.get("title"),
            raw_signal.get("label"),
            raw_signal.get("query"),
            fallback,
        ]

        for candidate in candidates:
            cleaned = _clean_text(candidate)
            if cleaned:
                return cleaned

        return "untitled_trend"

    def _normalize_label(self, value: str) -> str:
        cleaned = _clean_text(value, "untitled_trend").lower()
        cleaned = cleaned.replace("/", " ").replace("\\", " ")
        cleaned = "_".join(cleaned.split())
        return cleaned or "untitled_trend"

    def _normalize_platform(self, value: str) -> TrendPlatform:
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

    def _normalize_channel_targets(self, values: Any) -> list[str]:
        if not isinstance(values, list):
            return []

        alias_map = {
        "main": "main",
        "gaming_main": "main",
        "uncut": "uncut",
        "gaming_uncut": "uncut",
        "faceless": "faceless",
        "faceless_trend": "faceless",
    }

        normalized: list[str] = []
        seen: set[str] = set()

        for item in values:
            raw = _clean_text(item).lower()
            if not raw:
                continue

            mapped = alias_map.get(raw)
            if not mapped:
                continue

            if mapped in seen:
                continue

            seen.add(mapped)
            normalized.append(mapped)

        return normalized