from __future__ import annotations

import math
from typing import Any, Mapping

from core.real_vad_validation import (
    coverage_seconds,
    invert_regions_to_silence_gaps,
    merge_regions,
    speech_share_percent,
    total_duration,
)


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


def _subtract_intervals(
    base_start: float,
    base_end: float,
    blockers: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    chunks = [(base_start, base_end)]

    for block_start, block_end in blockers:
        next_chunks: list[tuple[float, float]] = []
        for start, end in chunks:
            if block_end <= start or block_start >= end:
                next_chunks.append((start, end))
                continue

            if block_start > start:
                next_chunks.append((start, min(block_start, end)))
            if block_end < end:
                next_chunks.append((max(block_end, start), end))

        chunks = next_chunks

    return [
        (_round_seconds(start), _round_seconds(end))
        for start, end in chunks
        if end > start
    ]


def combine_speech_regions(
    *,
    owner_regions: list[Mapping[str, Any]],
    friend_regions: list[Mapping[str, Any]],
    max_gap_seconds: float = 0.20,
    min_region_seconds: float = 0.15,
) -> list[dict[str, Any]]:
    raw: list[dict[str, Any]] = []

    for item in owner_regions:
        start = _safe_float(item.get("start_seconds"))
        end = _safe_float(item.get("end_seconds"))
        if end <= start:
            continue
        raw.append({
            "start_seconds": start,
            "end_seconds": end,
            "role": "owner",
        })

    for item in friend_regions:
        start = _safe_float(item.get("start_seconds"))
        end = _safe_float(item.get("end_seconds"))
        if end <= start:
            continue
        raw.append({
            "start_seconds": start,
            "end_seconds": end,
            "role": "friend",
        })

    merged = merge_regions(
        raw,
        max_gap_seconds=max_gap_seconds,
        min_region_seconds=min_region_seconds,
        source="combined_owner_or_friend_speech",
    )

    combined: list[dict[str, Any]] = []
    for index, item in enumerate(merged, start=1):
        start = _safe_float(item.get("start_seconds"))
        end = _safe_float(item.get("end_seconds"))

        owner_overlap = coverage_seconds(owner_regions, start_seconds=start, end_seconds=end)
        friend_overlap = coverage_seconds(friend_regions, start_seconds=start, end_seconds=end)

        roles: list[str] = []
        if owner_overlap > 0:
            roles.append("owner")
        if friend_overlap > 0:
            roles.append("friend")

        combined.append({
            "speech_region_id": f"combined_speech_{index:04d}",
            "start_seconds": _round_seconds(start),
            "end_seconds": _round_seconds(end),
            "duration_seconds": _duration(start, end),
            "source": "combined_owner_or_friend_speech",
            "roles": roles,
            "owner_overlap_seconds": owner_overlap,
            "friend_overlap_seconds": friend_overlap,
        })

    return combined


def build_combined_silence_gaps(
    *,
    combined_speech_regions: list[Mapping[str, Any]],
    media_duration_seconds: float,
) -> list[dict[str, Any]]:
    gaps = invert_regions_to_silence_gaps(
        combined_speech_regions,
        media_duration_seconds=media_duration_seconds,
        min_silence_seconds=0.05,
        source="combined_both_owner_and_friend_silent",
    )

    for index, item in enumerate(gaps, start=1):
        item["silence_gap_id"] = f"combined_silence_{index:04d}"
        item["source"] = "combined_both_owner_and_friend_silent"

    return gaps


def find_friend_speaks_owner_silent_examples(
    *,
    owner_regions: list[Mapping[str, Any]],
    friend_regions: list[Mapping[str, Any]],
    combined_regions: list[Mapping[str, Any]],
    min_duration_seconds: float = 0.60,
    limit: int = 5,
) -> list[dict[str, Any]]:
    owner_intervals = [
        (
            _safe_float(item.get("start_seconds")),
            _safe_float(item.get("end_seconds")),
        )
        for item in owner_regions
        if _safe_float(item.get("end_seconds")) > _safe_float(item.get("start_seconds"))
    ]

    examples: list[dict[str, Any]] = []

    for friend in friend_regions:
        friend_start = _safe_float(friend.get("start_seconds"))
        friend_end = _safe_float(friend.get("end_seconds"))

        if friend_end <= friend_start:
            continue

        blockers = [
            (start, end)
            for start, end in owner_intervals
            if _overlap_seconds(friend_start, friend_end, start, end) > 0
        ]

        friend_only_chunks = _subtract_intervals(friend_start, friend_end, blockers)

        for chunk_start, chunk_end in friend_only_chunks:
            chunk_duration = _duration(chunk_start, chunk_end)
            if chunk_duration < min_duration_seconds:
                continue

            combined_overlap = coverage_seconds(
                combined_regions,
                start_seconds=chunk_start,
                end_seconds=chunk_end,
            )

            examples.append({
                "start_seconds": chunk_start,
                "end_seconds": chunk_end,
                "duration_seconds": chunk_duration,
                "friend_region_start_seconds": _round_seconds(friend_start),
                "friend_region_end_seconds": _round_seconds(friend_end),
                "owner_overlap_seconds": coverage_seconds(
                    owner_regions,
                    start_seconds=chunk_start,
                    end_seconds=chunk_end,
                ),
                "combined_overlap_seconds": combined_overlap,
                "status": "PASS" if combined_overlap >= max(0.50, chunk_duration * 0.80) else "FAIL",
                "reason": "friend_speaks_owner_silent_now_counted_as_anyone_speech",
            })

    examples.sort(key=lambda item: item["duration_seconds"], reverse=True)
    return examples[:limit]


def build_combined_speech_summary(
    *,
    owner_regions: list[Mapping[str, Any]],
    friend_regions: list[Mapping[str, Any]],
    combined_regions: list[Mapping[str, Any]],
    combined_silence_gaps: list[Mapping[str, Any]],
    media_duration_seconds: float,
) -> dict[str, Any]:
    return {
        "media_duration_seconds": round(media_duration_seconds, 3),
        "owner_speech_region_count": len(owner_regions),
        "friend_speech_region_count": len(friend_regions),
        "combined_speech_region_count": len(combined_regions),
        "combined_silence_gap_count": len(combined_silence_gaps),
        "owner_speech_seconds": total_duration(list(owner_regions)),
        "friend_speech_seconds": total_duration(list(friend_regions)),
        "combined_speech_seconds": total_duration(list(combined_regions)),
        "combined_silence_seconds": total_duration(list(combined_silence_gaps)),
        "owner_speech_share_percent": speech_share_percent(owner_regions, media_duration_seconds=media_duration_seconds),
        "friend_speech_share_percent": speech_share_percent(friend_regions, media_duration_seconds=media_duration_seconds),
        "combined_speech_share_percent": speech_share_percent(combined_regions, media_duration_seconds=media_duration_seconds),
    }
