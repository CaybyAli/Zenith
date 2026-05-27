from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


INGEST_VERSION = "1"
FINGERPRINT_FILENAME = "style_fingerprint.json"

_ALLOWED_VIDEO_TYPES = {"gaming_main", "vlog_main"}
_ALLOWED_HOOK_CLASSES = {
    "question",
    "statement",
    "action",
    "name_drop",
    "unknown",
    "silent_start",
    "exclamation",
    "high_reaction",
    "narrative",
}

_REQUIRED_TOP_LEVEL_KEYS = (
    "video_id",
    "type",
    "quality_tier",
    "ingest_version",
    "ingest_timestamp_utc",
    "transcript",
    "scene_changes",
    "audio",
    "pacing",
    "hook",
    "reaction_timing",
)


def write_style_fingerprint(
    video_folder: str | Path,
    *,
    meta: dict[str, Any],
    transcript: dict[str, Any],
    scene_changes: dict[str, Any],
    audio: dict[str, Any],
    pacing: dict[str, Any],
    hook: dict[str, Any],
    reaction_timing: dict[str, Any],
    ingest_timestamp_utc: str | None = None,
) -> Path:
    """
    Write deterministic style_fingerprint.json next to a corpus video.

    The JSON is byte-stable for identical input except ingest_timestamp_utc.
    """

    folder = Path(video_folder)
    folder.mkdir(parents=True, exist_ok=True)

    fingerprint = build_style_fingerprint(
        meta=meta,
        transcript=transcript,
        scene_changes=scene_changes,
        audio=audio,
        pacing=pacing,
        hook=hook,
        reaction_timing=reaction_timing,
        ingest_timestamp_utc=ingest_timestamp_utc,
    )

    validate_style_fingerprint(fingerprint)

    output_path = folder / FINGERPRINT_FILENAME
    serialized = serialize_style_fingerprint(fingerprint)

    temp_path = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
    try:
        temp_path.write_text(serialized, encoding="utf-8", newline="\n")
        temp_path.replace(output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return output_path


def build_style_fingerprint(
    *,
    meta: dict[str, Any],
    transcript: dict[str, Any],
    scene_changes: dict[str, Any],
    audio: dict[str, Any],
    pacing: dict[str, Any],
    hook: dict[str, Any],
    reaction_timing: dict[str, Any],
    ingest_timestamp_utc: str | None = None,
) -> dict[str, Any]:
    """Build the exact P5-1 fingerprint schema."""

    meta = meta or {}
    timestamp = ingest_timestamp_utc or current_ingest_timestamp_utc()

    return {
        "video_id": _required_string(meta, "video_id"),
        "type": normalize_video_type(_required_string(meta, "type")),
        "quality_tier": _required_string(meta, "quality_tier"),
        "ingest_version": INGEST_VERSION,
        "ingest_timestamp_utc": timestamp,
        "transcript": {
            "language": str((transcript or {}).get("language", "unknown") or "unknown"),
            "segments_count": _safe_int((transcript or {}).get("segments_count", 0)),
            "first_10s_text": str((transcript or {}).get("first_10s_text", "") or ""),
        },
        "scene_changes": {
            "count": _safe_int((scene_changes or {}).get("count", 0)),
            "rate_per_minute": _safe_float((scene_changes or {}).get("rate_per_minute", 0)),
            "boundaries_seconds": _safe_float_list(
                (scene_changes or {}).get("boundaries_seconds", [])
            ),
        },
        "audio": {
            "lufs_integrated": _safe_float((audio or {}).get("lufs_integrated", 0)),
            "rms_curve_sampled": _safe_float_list(
                (audio or {}).get("rms_curve_sampled", [])
            ),
            "peak_db": _safe_float((audio or {}).get("peak_db", 0)),
        },
        "pacing": {
            "cut_count": _safe_int((pacing or {}).get("cut_count", 0)),
            "cuts_per_minute": _safe_float((pacing or {}).get("cuts_per_minute", 0)),
            "median_clip_seconds": _safe_float(
                (pacing or {}).get("median_clip_seconds", 0)
            ),
            "clip_length_histogram_bins": normalize_histogram_bins(
                (pacing or {}).get("clip_length_histogram_bins", [])
            ),
        },
        "hook": {
            "first_words": str((hook or {}).get("first_words", "") or ""),
            "pattern_class": normalize_hook_class(
                str((hook or {}).get("pattern_class", "unknown") or "unknown")
            ),
        },
        "reaction_timing": normalize_reaction_timing(reaction_timing or {}),
    }


def validate_style_fingerprint(fingerprint: dict[str, Any]) -> None:
    """Raise ValueError if the required P5-1 schema is incomplete."""

    if not isinstance(fingerprint, dict):
        raise ValueError("style fingerprint must be a dict")

    missing = [key for key in _REQUIRED_TOP_LEVEL_KEYS if key not in fingerprint]
    if missing:
        raise ValueError(f"style fingerprint missing top-level keys: {missing}")

    if fingerprint["type"] not in _ALLOWED_VIDEO_TYPES:
        raise ValueError(f"invalid video type: {fingerprint['type']!r}")

    if fingerprint["hook"]["pattern_class"] not in _ALLOWED_HOOK_CLASSES:
        raise ValueError(f"invalid hook pattern_class: {fingerprint['hook']['pattern_class']!r}")

    _require_keys(fingerprint["transcript"], ("language", "segments_count", "first_10s_text"), "transcript")
    _require_keys(fingerprint["scene_changes"], ("count", "rate_per_minute", "boundaries_seconds"), "scene_changes")
    _require_keys(fingerprint["audio"], ("lufs_integrated", "rms_curve_sampled", "peak_db"), "audio")
    _require_keys(
        fingerprint["pacing"],
        ("cut_count", "cuts_per_minute", "median_clip_seconds", "clip_length_histogram_bins"),
        "pacing",
    )
    _require_keys(fingerprint["hook"], ("first_words", "pattern_class"), "hook")
    _require_keys(fingerprint["reaction_timing"], ("applicable",), "reaction_timing")

    if fingerprint["reaction_timing"].get("applicable") is True:
        _require_keys(fingerprint["reaction_timing"], ("events",), "reaction_timing")


def serialize_style_fingerprint(fingerprint: dict[str, Any]) -> str:
    """Serialize deterministically with stable sorting and trailing newline."""

    return (
        json.dumps(
            fingerprint,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
        )
        + "\n"
    )


def fingerprint_for_determinism_compare(fingerprint: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy without ingest_timestamp_utc."""

    comparable = copy.deepcopy(fingerprint)
    comparable.pop("ingest_timestamp_utc", None)
    return comparable


def current_ingest_timestamp_utc() -> str:
    """Return an ISO-8601 UTC timestamp with second precision."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_video_type(value: str) -> str:
    """
    Normalize known corpus type aliases into the required schema values.

    top_main is a solo gaming-main corpus bucket, so it maps to gaming_main.
    """

    clean = str(value or "").strip().lower()
    aliases = {
        "gaming": "gaming_main",
        "gaming_main": "gaming_main",
        "top_main": "gaming_main",
        "top_solo": "gaming_main",
        "pair": "gaming_main",
        "pairs": "gaming_main",
        "vlog": "vlog_main",
        "vlogs": "vlog_main",
        "vlog_main": "vlog_main",
    }
    return aliases.get(clean, clean)


def normalize_hook_class(value: str) -> str:
    clean = str(value or "").strip().lower()
    if clean in _ALLOWED_HOOK_CLASSES:
        return clean
    return "unknown"


def normalize_reaction_timing(value: dict[str, Any]) -> dict[str, Any]:
    applicable = bool((value or {}).get("applicable", False))
    if not applicable:
        return {"applicable": False}

    events = value.get("events", [])
    if not isinstance(events, list):
        events = []

    normalized_events: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue

        normalized_events.append(
            {
                "time_seconds": _safe_float(event.get("time_seconds", 0)),
                "kind": str(event.get("kind", "unknown") or "unknown"),
                "confidence": _safe_float(event.get("confidence", 0)),
                "reason": str(event.get("reason", "") or ""),
            }
        )

    return {"applicable": True, "events": normalized_events}


def normalize_histogram_bins(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue

        max_seconds = item.get("max_seconds", None)
        normalized.append(
            {
                "label": str(item.get("label", "") or ""),
                "min_seconds": _safe_float(item.get("min_seconds", 0)),
                "max_seconds": None if max_seconds is None else _safe_float(max_seconds),
                "count": _safe_int(item.get("count", 0)),
            }
        )

    return normalized


def _required_string(meta: dict[str, Any], key: str) -> str:
    value = str((meta or {}).get(key, "") or "").strip()
    if not value:
        raise ValueError(f"meta.{key} is required")
    return value


def _require_keys(value: Any, keys: tuple[str, ...], label: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a dict")

    missing = [key for key in keys if key not in value]
    if missing:
        raise ValueError(f"{label} missing keys: {missing}")


def _safe_int(value: Any) -> int:
    try:
        converted = int(value)
    except (TypeError, ValueError):
        return 0

    return max(converted, 0)


def _safe_float(value: Any) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return 0.0

    return round(converted, 6)


def _safe_float_list(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []

    return [_safe_float(item) for item in value]
