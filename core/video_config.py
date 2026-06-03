from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip().lstrip("\ufeff"))
    except Exception:
        return default
    return number if math.isfinite(number) else default


def read_video_config(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(data, Mapping):
        raise ValueError(f"video config must be a JSON object: {config_path}")
    return dict(data)


def _range_kind(key: Any, row: Mapping[str, Any]) -> str:
    value = (
        row.get("range_type")
        or row.get("kind")
        or row.get("type")
        or row.get("role")
        or row.get("name")
        or row.get("range_id")
        or row.get("id")
        or key
        or ""
    )
    return str(value).strip().lower()


def _default_protection_mode(kind: str) -> str:
    if "payoff" in kind:
        return "hard_lock"
    if "combat" in kind or "fight" in kind:
        return "event_or_high_visual_not_blanket_lock"
    return "configured_protected_range"


def _iter_range_rows(raw: Any) -> list[tuple[Any, Mapping[str, Any]]]:
    if isinstance(raw, Mapping):
        if any(key in raw for key in ("start_seconds", "start", "start_time", "begin")):
            return [("", raw)]
        rows: list[tuple[Any, Mapping[str, Any]]] = []
        for key, value in raw.items():
            if isinstance(value, Mapping):
                rows.append((key, value))
            elif isinstance(value, list):
                rows.extend((key, item) for item in value if isinstance(item, Mapping))
        return rows
    if isinstance(raw, list):
        return [("", item) for item in raw if isinstance(item, Mapping)]
    return []


def normalize_protected_ranges(config_or_ranges: Any) -> list[dict[str, Any]]:
    if isinstance(config_or_ranges, Mapping) and "protected_ranges" in config_or_ranges:
        raw = config_or_ranges.get("protected_ranges")
    else:
        raw = config_or_ranges

    ranges: list[dict[str, Any]] = []
    for key, row in _iter_range_rows(raw):
        start = safe_float(
            row.get("start_seconds", row.get("start", row.get("start_time", row.get("begin")))),
            math.nan,
        )
        end = safe_float(
            row.get("end_seconds", row.get("end", row.get("end_time", row.get("stop")))),
            math.nan,
        )
        if not math.isfinite(start) or not math.isfinite(end) or end <= start:
            continue

        kind = _range_kind(key, row)
        item = dict(row)
        item["start_seconds"] = round(start, 3)
        item["end_seconds"] = round(end, 3)
        item.setdefault("reason", f"{kind}_protected_range" if kind else "protected_range")
        item.setdefault("protection_mode", _default_protection_mode(kind))
        ranges.append(item)

    return sorted(ranges, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def protected_range_for_kind(config_or_ranges: Any, kind: str) -> dict[str, Any] | None:
    needle = kind.strip().lower()
    for row in normalize_protected_ranges(config_or_ranges):
        haystack = " ".join(
            str(row.get(key, ""))
            for key in ("range_type", "range_id", "kind", "type", "role", "name", "reason")
        ).lower()
        if needle in haystack:
            return row
    return None
