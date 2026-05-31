from __future__ import annotations

import math
from typing import Any, Mapping


KNOWN_SPEECH_WINDOWS = [
    {
        "name": "busfahrer_speech_around_287",
        "start_seconds": 284.0,
        "end_seconds": 292.0,
        "min_speech_overlap_seconds": 0.5,
    },
    {
        "name": "achsoooo_speech_around_767",
        "start_seconds": 766.0,
        "end_seconds": 774.0,
        "min_speech_overlap_seconds": 0.3,
    },
    {
        "name": "death_talk_1786_to_1810",
        "start_seconds": 1786.0,
        "end_seconds": 1810.5,
        "min_speech_overlap_seconds": 3.0,
    },
]

KNOWN_SILENCE_WINDOWS = [
    {
        "name": "between_rounds_silence_599_to_615",
        "start_seconds": 599.15,
        "end_seconds": 615.46,
        "min_silence_overlap_seconds": 8.0,
    },
    {
        "name": "stretched_richtig_silence_258_to_278",
        "start_seconds": 258.62,
        "end_seconds": 278.62,
        "min_silence_overlap_seconds": 10.0,
    },
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except Exception:
        return default
    if not math.isfinite(number):
        return default
    return number


def _round_seconds(value: Any) -> float:
    return round(max(0.0, _safe_float(value)), 3)


def _duration(start: float, end: float) -> float:
    return round(max(0.0, float(end) - float(start)), 3)


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def normalize_regions(raw_regions: Any, *, source: str = "real_vad") -> list[dict[str, Any]]:
    if isinstance(raw_regions, Mapping):
        for key in ("speech_regions", "regions", "segments", "items"):
            if isinstance(raw_regions.get(key), list):
                raw_regions = raw_regions[key]
                break

    if not isinstance(raw_regions, list):
        return []

    regions: list[dict[str, Any]] = []
    for index, item in enumerate(raw_regions, start=1):
        if not isinstance(item, Mapping):
            continue

        start = item.get("start_seconds", item.get("start", item.get("start_time")))
        end = item.get("end_seconds", item.get("end", item.get("end_time")))

        if start is None or end is None:
            continue

        start_f = _round_seconds(start)
        end_f = _round_seconds(end)
        if end_f <= start_f:
            continue

        regions.append({
            "speech_region_id": str(item.get("speech_region_id") or item.get("id") or f"real_vad_speech_{index:04d}"),
            "start_seconds": start_f,
            "end_seconds": end_f,
            "duration_seconds": _duration(start_f, end_f),
            "source": str(item.get("source") or source),
        })

    return sorted(regions, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def merge_regions(
    regions: list[Mapping[str, Any]],
    *,
    max_gap_seconds: float = 0.20,
    min_region_seconds: float = 0.15,
    source: str = "real_vad_merged",
) -> list[dict[str, Any]]:
    ordered = normalize_regions(regions, source=source)
    merged: list[dict[str, Any]] = []

    for item in ordered:
        if not merged:
            merged.append(dict(item))
            continue

        previous = merged[-1]
        gap = item["start_seconds"] - previous["end_seconds"]

        if gap <= max_gap_seconds:
            previous["end_seconds"] = max(previous["end_seconds"], item["end_seconds"])
            previous["duration_seconds"] = _duration(previous["start_seconds"], previous["end_seconds"])
        else:
            merged.append(dict(item))

    final: list[dict[str, Any]] = []
    for index, item in enumerate(merged, start=1):
        if item["duration_seconds"] < min_region_seconds:
            continue
        final.append({
            "speech_region_id": f"real_vad_speech_{index:04d}",
            "start_seconds": _round_seconds(item["start_seconds"]),
            "end_seconds": _round_seconds(item["end_seconds"]),
            "duration_seconds": _duration(item["start_seconds"], item["end_seconds"]),
            "source": source,
        })

    return final


def invert_regions_to_silence_gaps(
    speech_regions: list[Mapping[str, Any]],
    *,
    media_duration_seconds: float,
    min_silence_seconds: float = 0.05,
    source: str = "real_vad_silence",
) -> list[dict[str, Any]]:
    merged = merge_regions(
        list(speech_regions),
        max_gap_seconds=0.0,
        min_region_seconds=0.0,
        source="tmp",
    )

    gaps: list[dict[str, Any]] = []
    cursor = 0.0
    media_end = _round_seconds(media_duration_seconds)

    for region in merged:
        start = _round_seconds(region["start_seconds"])
        end = _round_seconds(region["end_seconds"])

        if start > cursor:
            duration = _duration(cursor, start)
            if duration >= min_silence_seconds:
                gaps.append({
                    "silence_gap_id": f"real_vad_silence_{len(gaps) + 1:04d}",
                    "start_seconds": _round_seconds(cursor),
                    "end_seconds": start,
                    "duration_seconds": duration,
                    "source": source,
                })

        cursor = max(cursor, end)

    if cursor < media_end:
        duration = _duration(cursor, media_end)
        if duration >= min_silence_seconds:
            gaps.append({
                "silence_gap_id": f"real_vad_silence_{len(gaps) + 1:04d}",
                "start_seconds": _round_seconds(cursor),
                "end_seconds": media_end,
                "duration_seconds": duration,
                "source": source,
            })

    return gaps


def total_duration(items: list[Mapping[str, Any]]) -> float:
    return round(sum(_safe_float(item.get("duration_seconds")) for item in items), 3)


def coverage_seconds(
    regions: list[Mapping[str, Any]],
    *,
    start_seconds: float,
    end_seconds: float,
) -> float:
    total = 0.0
    for region in regions:
        total += _overlap_seconds(
            start_seconds,
            end_seconds,
            _safe_float(region.get("start_seconds")),
            _safe_float(region.get("end_seconds")),
        )
    return round(total, 3)


def speech_share_percent(
    speech_regions: list[Mapping[str, Any]],
    *,
    media_duration_seconds: float,
) -> float:
    if media_duration_seconds <= 0:
        return 0.0
    speech_seconds = total_duration(list(speech_regions))
    return round((speech_seconds / media_duration_seconds) * 100.0, 3)


def validate_real_vad_windows(
    *,
    speech_regions: list[Mapping[str, Any]],
    silence_gaps: list[Mapping[str, Any]],
    media_duration_seconds: float,
) -> dict[str, Any]:
    speech_checks: list[dict[str, Any]] = []
    silence_checks: list[dict[str, Any]] = []

    for spec in KNOWN_SPEECH_WINDOWS:
        start = float(spec["start_seconds"])
        end = float(spec["end_seconds"])
        overlap = coverage_seconds(speech_regions, start_seconds=start, end_seconds=end)
        min_overlap = float(spec["min_speech_overlap_seconds"])
        speech_checks.append({
            "name": spec["name"],
            "range_seconds": [start, end],
            "speech_overlap_seconds": overlap,
            "min_required_seconds": min_overlap,
            "status": "PASS" if overlap >= min_overlap else "FAIL",
        })

    for spec in KNOWN_SILENCE_WINDOWS:
        start = float(spec["start_seconds"])
        end = float(spec["end_seconds"])
        overlap = coverage_seconds(silence_gaps, start_seconds=start, end_seconds=end)
        min_overlap = float(spec["min_silence_overlap_seconds"])
        silence_checks.append({
            "name": spec["name"],
            "range_seconds": [start, end],
            "silence_overlap_seconds": overlap,
            "min_required_seconds": min_overlap,
            "status": "PASS" if overlap >= min_overlap else "FAIL",
        })

    share = speech_share_percent(speech_regions, media_duration_seconds=media_duration_seconds)
    share_status = "PASS" if 40.0 <= share <= 60.0 else "FAIL"

    failed = [
        item for item in speech_checks + silence_checks
        if item["status"] != "PASS"
    ]
    if share_status != "PASS":
        failed.append({
            "name": "speech_share_plausibility_40_to_60_percent",
            "status": "FAIL",
            "speech_share_percent": share,
        })

    return {
        "speech_share_percent": share,
        "speech_share_expected_range_percent": [40.0, 60.0],
        "speech_share_status": share_status,
        "known_speech_checks": speech_checks,
        "known_silence_checks": silence_checks,
        "failed_count": len(failed),
        "overall_status": "PASS" if not failed else "FAIL",
    }
