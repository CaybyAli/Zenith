from __future__ import annotations

import copy
from typing import Any, Mapping

ROUND_PAYOFF_TAIL_ROLE = "round_payoff_tail"
PAYOFF_2_SOURCE = "payoff_2_adaptive_reaction_gate"
DEFAULT_TAIL_MAX_SECONDS = 20.0

INTENSITY_RANK = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
}


def _round_seconds(value: Any) -> float:
    return round(max(0.0, float(value)), 3)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _duration(start: float, end: float) -> float:
    return round(max(0.0, float(end) - float(start)), 3)


def _field(item: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(item, Mapping) and name in item:
            return item[name]
        if hasattr(item, name):
            return getattr(item, name)
    return default


def _rank(value: str) -> int:
    return INTENSITY_RANK.get(str(value).lower(), 0)


def _segment_role(item: Mapping[str, Any]) -> str:
    return str(item.get("segment_role") or item.get("state") or "")


def _is_payoff_tail_segment(item: Mapping[str, Any]) -> bool:
    return _segment_role(item) == ROUND_PAYOFF_TAIL_ROLE or bool(item.get("payoff_tail"))


def _is_active_timeline_segment(item: Mapping[str, Any]) -> bool:
    return str(item.get("state") or "") == "active_play" and not _is_payoff_tail_segment(item)


def _text_from_words(words: list[Mapping[str, Any]], start: float, end: float) -> str:
    tokens: list[str] = []
    for word in words:
        word_start = _safe_float(_field(word, "start_seconds", "start", "start_time", default=None))
        word_end = _safe_float(_field(word, "end_seconds", "end", "end_time", default=None))
        token = str(_field(word, "word", "text", default="") or "").strip()
        if not token:
            continue
        if word_end > start and word_start < end:
            tokens.append(token)
    return " ".join(tokens).strip()


def normalize_words(raw_words: Any) -> list[dict[str, Any]]:
    if isinstance(raw_words, Mapping):
        for key in ("words", "word_timestamps", "items"):
            value = raw_words.get(key)
            if isinstance(value, list):
                raw_words = value
                break

    if not isinstance(raw_words, list):
        return []

    words: list[dict[str, Any]] = []
    for item in raw_words:
        if not isinstance(item, Mapping):
            continue
        start = _field(item, "start_seconds", "start", "start_time", default=None)
        end = _field(item, "end_seconds", "end", "end_time", default=None)
        text = str(_field(item, "word", "text", default="") or "").strip()
        if start is None or end is None or not text:
            continue
        if float(end) <= float(start):
            continue
        words.append({
            "word": text,
            "start_seconds": _round_seconds(start),
            "end_seconds": _round_seconds(end),
        })
    return sorted(words, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def normalize_speech_segments(raw_segments: Any, *, words: list[Mapping[str, Any]] | None = None) -> list[dict[str, Any]]:
    if isinstance(raw_segments, Mapping):
        for key in ("speech_segments", "segments", "items"):
            value = raw_segments.get(key)
            if isinstance(value, list):
                raw_segments = value
                break

    if not isinstance(raw_segments, list):
        return []

    word_items = list(words or [])
    result: list[dict[str, Any]] = []

    for index, item in enumerate(raw_segments, start=1):
        if not isinstance(item, Mapping):
            continue
        start = _field(item, "start_seconds", "start", "start_time", default=None)
        end = _field(item, "end_seconds", "end", "end_time", default=None)
        if start is None or end is None:
            continue
        if float(end) <= float(start):
            continue

        start_f = _round_seconds(start)
        end_f = _round_seconds(end)
        text = str(_field(item, "text", "transcript", default="") or "").strip()
        if not text and word_items:
            text = _text_from_words(word_items, start_f, end_f)

        result.append({
            "speech_segment_id": str(_field(item, "speech_segment_id", "segment_id", "id", default=f"speech_{index:04d}")),
            "start_seconds": start_f,
            "end_seconds": end_f,
            "duration_seconds": _duration(start_f, end_f),
            "text": text,
        })

    return sorted(result, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def normalize_reaction_events(raw_events: Any) -> list[dict[str, Any]]:
    if isinstance(raw_events, Mapping):
        for key in ("reactions", "events", "items"):
            value = raw_events.get(key)
            if isinstance(value, list):
                raw_events = value
                break

    if not isinstance(raw_events, list):
        return []

    events: list[dict[str, Any]] = []

    for index, item in enumerate(raw_events, start=1):
        if not isinstance(item, Mapping):
            continue

        start = _field(item, "start_seconds", "start", default=None)
        end = _field(item, "end_seconds", "end", default=None)
        peak = _field(item, "peak_time_seconds", "time_seconds", "peak", default=start)

        if start is None:
            start = peak
        if end is None:
            end = peak

        start_f = _round_seconds(start)
        end_f = _round_seconds(end)
        peak_f = _round_seconds(peak)

        intensity = str(_field(item, "intensity", "reaction_intensity", default="none") or "none").lower()

        events.append({
            "reaction_id": str(_field(item, "reaction_id", "id", default=f"reaction_{index:04d}")),
            "start_seconds": start_f,
            "end_seconds": max(start_f, end_f),
            "peak_time_seconds": peak_f,
            "peak_timestamp": str(_field(item, "peak_timestamp", "timestamp", default="")),
            "intensity": intensity,
            "rank": _rank(intensity),
            "fusion_score": _safe_float(_field(item, "fusion_score", "score", default=0.0)),
            "mic_audio_rise_db": _safe_float(_field(item, "mic_audio_rise_db", "mic_rise", default=0.0)),
            "text": str(_field(item, "text", default="") or "").strip(),
        })

    return sorted(events, key=lambda item: (item["peak_time_seconds"], item["start_seconds"]))


def _clean_existing_payoff_tails(plan_data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    cleaned = copy.deepcopy(plan_data)
    original_segments = list(cleaned.get("timeline_segments") or [])
    kept_segments = [
        segment for segment in original_segments
        if isinstance(segment, Mapping) and not _is_payoff_tail_segment(segment)
    ]
    removed = len(original_segments) - len(kept_segments)
    cleaned["timeline_segments"] = kept_segments
    cleaned.pop("payoff_tails", None)
    cleaned.pop("payoff_tail_audit", None)
    cleaned.pop("payoff_tail_contract", None)
    return cleaned, removed


def _active_block_ranges(timeline_segments: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_block: dict[str, list[Mapping[str, Any]]] = {}

    for item in timeline_segments:
        if not isinstance(item, Mapping):
            continue
        if not _is_active_timeline_segment(item):
            continue
        block_id = str(item.get("block_id") or "")
        if not block_id:
            continue
        by_block.setdefault(block_id, []).append(item)

    blocks: list[dict[str, Any]] = []
    for block_id, items in by_block.items():
        ranges: list[tuple[float, float]] = []
        for item in items:
            start = _field(item, "start_seconds", "start", "start_time", default=None)
            end = _field(item, "end_seconds", "end", "end_time", default=None)
            if start is None or end is None:
                continue
            if float(end) <= float(start):
                continue
            ranges.append((_round_seconds(start), _round_seconds(end)))

        if ranges:
            ranges = sorted(ranges)
            blocks.append({
                "block_id": block_id,
                "start_seconds": ranges[0][0],
                "end_seconds": ranges[-1][1],
                "active_ranges": [
                    {"start_seconds": start, "end_seconds": end, "duration_seconds": _duration(start, end)}
                    for start, end in ranges
                ],
            })

    return sorted(blocks, key=lambda item: (item["start_seconds"], item["end_seconds"], item["block_id"]))


def _speech_hits_in_window(
    speech_segments: list[Mapping[str, Any]],
    *,
    window_start: float,
    window_end: float,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []

    for speech in speech_segments:
        start = _safe_float(_field(speech, "start_seconds", "start", "start_time", default=None))
        end = _safe_float(_field(speech, "end_seconds", "end", "end_time", default=None))
        if end <= window_start or start >= window_end:
            continue

        clipped_start = max(window_start, start)
        clipped_end = min(window_end, end)
        if clipped_end <= clipped_start:
            continue

        hits.append({
            "speech_segment_id": str(_field(speech, "speech_segment_id", "segment_id", "id", default="")),
            "start_seconds": _round_seconds(start),
            "end_seconds": _round_seconds(end),
            "clipped_start_seconds": _round_seconds(clipped_start),
            "clipped_end_seconds": _round_seconds(clipped_end),
            "text": str(_field(speech, "text", "transcript", default="") or "").strip(),
        })

    return sorted(hits, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def _reaction_overlaps_window(reaction: Mapping[str, Any], window_start: float, window_end: float) -> bool:
    peak = _safe_float(reaction.get("peak_time_seconds"))
    start = _safe_float(reaction.get("start_seconds"))
    end = _safe_float(reaction.get("end_seconds"))

    peak_inside = window_start <= peak < window_end
    overlap_inside = end > window_start and start < window_end

    return peak_inside or overlap_inside


def _normalized_reaction_item(reaction: Mapping[str, Any]) -> dict[str, Any]:
    item = dict(reaction)
    intensity = str(item.get("intensity") or item.get("reaction_intensity") or "none").lower()
    item["intensity"] = intensity
    item["rank"] = int(item.get("rank") or _rank(intensity))
    item["fusion_score"] = _safe_float(item.get("fusion_score") or item.get("score") or 0.0)
    item["mic_audio_rise_db"] = _safe_float(item.get("mic_audio_rise_db") or item.get("mic_rise") or 0.0)
    item["peak_time_seconds"] = item.get("peak_time_seconds", item.get("time_seconds"))
    item["peak_timestamp"] = item.get("peak_timestamp", item.get("timestamp"))
    return item


def _best_reaction_in_window(
    reaction_events: list[Mapping[str, Any]],
    *,
    window_start: float,
    window_end: float,
) -> dict[str, Any]:
    hits = [
        _normalized_reaction_item(reaction)
        for reaction in reaction_events
        if _reaction_overlaps_window(reaction, window_start, window_end)
    ]

    if not hits:
        return {
            "reaction_id": None,
            "intensity": "none",
            "rank": 0,
            "fusion_score": 0.0,
            "mic_audio_rise_db": 0.0,
            "peak_time_seconds": None,
            "peak_timestamp": None,
            "text": "",
        }

    return max(
        hits,
        key=lambda item: (
            int(item.get("rank") or 0),
            _safe_float(item.get("mic_audio_rise_db")),
            _safe_float(item.get("fusion_score")),
        ),
    )


def apply_round_payoff_tails_with_reaction_gate(
    plan_data: dict[str, Any],
    speech_segments: list[Mapping[str, Any]],
    reaction_events: list[Mapping[str, Any]],
    *,
    media_duration_seconds: float,
    tail_max_seconds: float = DEFAULT_TAIL_MAX_SECONDS,
    reaction_min_intensity: str = "medium",
) -> dict[str, Any]:
    if tail_max_seconds < 0:
        raise ValueError("tail_max_seconds must be >= 0")

    min_rank = _rank(reaction_min_intensity)
    cleaned_plan, removed_existing_tail_count = _clean_existing_payoff_tails(plan_data)
    timeline_segments = list(cleaned_plan.get("timeline_segments") or [])
    active_blocks = _active_block_ranges(timeline_segments)
    media_end = _round_seconds(media_duration_seconds)
    tail_max = _round_seconds(tail_max_seconds)

    payoff_tails: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []

    for index, block in enumerate(active_blocks):
        block_end = _round_seconds(block["end_seconds"])
        next_block_start = (
            _round_seconds(active_blocks[index + 1]["start_seconds"])
            if index + 1 < len(active_blocks)
            else media_end
        )
        dead_zone_end = min(media_end, next_block_start)
        window_start = block_end
        window_end = min(dead_zone_end, block_end + tail_max)

        best_reaction = _best_reaction_in_window(
            reaction_events,
            window_start=window_start,
            window_end=window_end,
        )
        best_rank = int(best_reaction.get("rank") or 0)
        reaction_gate_pass = best_rank >= min_rank

        evaluation = {
            "block_id": block["block_id"],
            "original_block_end_seconds": block_end,
            "next_block_start_seconds": next_block_start,
            "tail_window_start_seconds": window_start,
            "tail_window_end_seconds": _round_seconds(window_end),
            "best_reaction_intensity": str(best_reaction.get("intensity") or "none").upper(),
            "best_reaction_rank": best_rank,
            "best_reaction_id": best_reaction.get("reaction_id"),
            "best_reaction_peak_time_seconds": best_reaction.get("peak_time_seconds"),
            "best_reaction_peak_timestamp": best_reaction.get("peak_timestamp"),
            "best_reaction_fusion_score": _safe_float(best_reaction.get("fusion_score")),
            "best_reaction_mic_audio_rise_db": _safe_float(best_reaction.get("mic_audio_rise_db")),
            "reaction_gate_pass": reaction_gate_pass,
            "tail_added": False,
            "reason": "",
            "speech_hits": [],
        }

        if window_end <= window_start:
            evaluation["reason"] = "no_dead_zone_after_block"
            evaluations.append(evaluation)
            continue

        if not reaction_gate_pass:
            evaluation["reason"] = "reaction_below_min_intensity"
            evaluations.append(evaluation)
            continue

        speech_hits = _speech_hits_in_window(
            speech_segments,
            window_start=window_start,
            window_end=window_end,
        )
        evaluation["speech_hits"] = speech_hits

        if not speech_hits:
            evaluation["reason"] = "reaction_found_but_no_speech_segment_to_extend"
            evaluations.append(evaluation)
            continue

        tail_end = max(float(hit["clipped_end_seconds"]) for hit in speech_hits)
        tail_end = min(tail_end, block_end + tail_max, dead_zone_end, media_end)
        tail_end = _round_seconds(tail_end)

        if tail_end <= block_end:
            evaluation["reason"] = "speech_does_not_extend_after_block_end"
            evaluations.append(evaluation)
            continue

        speech_text = " ".join(
            str(hit.get("text") or "").strip()
            for hit in speech_hits
            if str(hit.get("text") or "").strip()
        ).strip()

        tail_index = len(payoff_tails) + 1
        tail_segment = {
            "segment_id": f"{block['block_id']}_round_payoff_tail_{tail_index:03d}",
            "block_id": block["block_id"],
            "start_seconds": block_end,
            "end_seconds": tail_end,
            "duration_seconds": _duration(block_end, tail_end),
            "state": ROUND_PAYOFF_TAIL_ROLE,
            "segment_role": ROUND_PAYOFF_TAIL_ROLE,
            "keep_decision": "keep_round_payoff_tail_reaction_gated",
            "source": PAYOFF_2_SOURCE,
            "payoff_tail": True,
            "metadata": {
                "reaction_gate": "adaptive_reaction",
                "reaction_min_intensity": str(reaction_min_intensity).lower(),
                "best_reaction": best_reaction,
                "original_block_end_seconds": block_end,
                "tail_max_seconds": tail_max,
                "speech_segment_count": len(speech_hits),
                "speech_text": speech_text,
                "trailing_silence_trimmed": tail_end < _round_seconds(window_end),
            },
        }

        payoff_tails.append(tail_segment)
        evaluation["tail_added"] = True
        evaluation["reason"] = "reaction_gate_passed_tail_added_until_last_speech_end"
        evaluation["new_block_end_seconds"] = tail_end
        evaluation["tail_duration_seconds"] = _duration(block_end, tail_end)
        evaluations.append(evaluation)

    new_timeline_segments = [
        dict(segment)
        for segment in timeline_segments
        if isinstance(segment, Mapping)
    ] + payoff_tails

    new_timeline_segments = sorted(
        new_timeline_segments,
        key=lambda item: (
            float(item.get("start_seconds") or 0.0),
            float(item.get("end_seconds") or 0.0),
            str(item.get("segment_id") or ""),
        ),
    )

    for item in new_timeline_segments:
        item["duration_seconds"] = _duration(
            float(item.get("start_seconds") or 0.0),
            float(item.get("end_seconds") or 0.0),
        )

    original_duration = round(
        sum(float(item.get("duration_seconds") or 0.0) for item in timeline_segments),
        3,
    )
    new_duration = round(
        sum(float(item.get("duration_seconds") or 0.0) for item in new_timeline_segments),
        3,
    )
    added_tail_seconds = round(new_duration - original_duration, 3)

    cleaned_plan["timeline_segments"] = new_timeline_segments
    cleaned_plan["payoff_tails"] = payoff_tails
    cleaned_plan["payoff_tail_audit"] = {
        "engine": PAYOFF_2_SOURCE,
        "tail_max_seconds": tail_max,
        "reaction_min_intensity": str(reaction_min_intensity).lower(),
        "tail_count": len(payoff_tails),
        "added_tail_seconds": added_tail_seconds,
        "anti_overcut_fail_count": 0,
        "removed_active_play_seconds": 0.0,
        "removed_existing_payoff_tail_count": removed_existing_tail_count,
        "evaluations": evaluations,
    }
    cleaned_plan["payoff_tail_contract"] = {
        "original_planned_output_duration_seconds": original_duration,
        "new_planned_output_duration_seconds": new_duration,
        "added_tail_seconds": added_tail_seconds,
        "tail_max_seconds": tail_max,
        "reaction_min_intensity": str(reaction_min_intensity).lower(),
        "segment_role": ROUND_PAYOFF_TAIL_ROLE,
    }

    duration_contract = dict(cleaned_plan.get("duration_contract") or {})
    duration_contract["planned_output_duration_seconds"] = new_duration
    duration_contract["payoff_tail_added_seconds"] = added_tail_seconds
    cleaned_plan["duration_contract"] = duration_contract

    notes = list(cleaned_plan.get("notes") or [])
    notes.append(
        f"payoff_2_adaptive_reaction_gate tail_max_seconds={tail_max:.3f} "
        f"reaction_min_intensity={str(reaction_min_intensity).lower()} "
        f"added_tail_seconds={added_tail_seconds:.3f}"
    )
    cleaned_plan["notes"] = notes

    return cleaned_plan
