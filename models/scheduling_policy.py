from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _clean_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"true", "1", "yes", "on"}:
            return True
        if cleaned in {"false", "0", "no", "off"}:
            return False
    return default


def _clean_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        numeric = default

    return max(minimum, min(maximum, numeric))


def _clean_days(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []

    cleaned: list[int] = []
    for item in values:
        try:
            numeric = int(item)
        except (TypeError, ValueError):
            continue

        if 0 <= numeric <= 6 and numeric not in cleaned:
            cleaned.append(numeric)

    return sorted(cleaned)


@dataclass(slots=True)
class SchedulingPolicy:
    channel_type: str

    is_enabled: bool = True
    allows_longform: bool = True
    allows_shorts: bool = False

    publish_days: list[int] = field(default_factory=list)
    publish_hour: int = 17
    publish_minute: int = 0
    min_gap_hours: int = 24

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SchedulingPolicy":
        return cls(
            channel_type=_clean_text(data.get("channel_type"), "unknown_channel"),
            is_enabled=_clean_bool(data.get("is_enabled"), True),
            allows_longform=_clean_bool(data.get("allows_longform"), True),
            allows_shorts=_clean_bool(data.get("allows_shorts"), False),
            publish_days=_clean_days(data.get("publish_days")),
            publish_hour=_clean_int(data.get("publish_hour"), 17, 0, 23),
            publish_minute=_clean_int(data.get("publish_minute"), 0, 0, 59),
            min_gap_hours=_clean_int(data.get("min_gap_hours"), 24, 1, 168),
            created_at=_clean_text(data.get("created_at")) or utc_now_iso(),
            updated_at=_clean_text(data.get("updated_at")) or utc_now_iso(),
        )