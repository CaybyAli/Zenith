from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


DEFAULT_SAMPLE_RATE = 16000
DEFAULT_FRAME_SECONDS = 0.03
DEFAULT_MIN_SPEECH_SECONDS = 0.25
DEFAULT_MIN_SILENCE_SECONDS = 0.20
DEFAULT_SPEECH_PAD_SECONDS = 0.08


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


def _field(item: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(item, Mapping) and name in item:
            return item[name]
        if hasattr(item, name):
            return getattr(item, name)
    return default


def percentile(values: list[float], pct: float, *, default: float = 0.0) -> float:
    cleaned = sorted(float(v) for v in values if math.isfinite(float(v)))
    if not cleaned:
        return default
    if len(cleaned) == 1:
        return round(cleaned[0], 6)

    pct = max(0.0, min(100.0, float(pct)))
    pos = (len(cleaned) - 1) * (pct / 100.0)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return round(cleaned[lo], 6)

    weight = pos - lo
    return round(cleaned[lo] + ((cleaned[hi] - cleaned[lo]) * weight), 6)


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def normalize_words(raw_words: Any) -> list[dict[str, Any]]:
    if isinstance(raw_words, Mapping):
        for key in ("words", "word_timestamps", "items"):
            if isinstance(raw_words.get(key), list):
                raw_words = raw_words[key]
                break

    if not isinstance(raw_words, list):
        return []

    words: list[dict[str, Any]] = []
    for index, item in enumerate(raw_words, start=1):
        if not isinstance(item, Mapping):
            continue

        word = str(_field(item, "word", "text", default="") or "").strip()
        start = _field(item, "start_seconds", "start", "start_time", default=None)
        end = _field(item, "end_seconds", "end", "end_time", default=None)

        if start is None or end is None or not word:
            continue

        start_f = _round_seconds(start)
        end_f = _round_seconds(end)

        if end_f <= start_f:
            continue

        words.append({
            "word_id": str(_field(item, "word_id", "id", default=f"word_{index:05d}")),
            "word": word,
            "start_seconds": start_f,
            "end_seconds": end_f,
            "duration_seconds": _duration(start_f, end_f),
        })

    return sorted(words, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def normalize_speech_segments(raw_segments: Any) -> list[dict[str, Any]]:
    if isinstance(raw_segments, Mapping):
        for key in ("speech_segments", "segments", "items"):
            if isinstance(raw_segments.get(key), list):
                raw_segments = raw_segments[key]
                break

    if not isinstance(raw_segments, list):
        return []

    segments: list[dict[str, Any]] = []
    for index, item in enumerate(raw_segments, start=1):
        if not isinstance(item, Mapping):
            continue

        start = _field(item, "start_seconds", "start", "start_time", default=None)
        end = _field(item, "end_seconds", "end", "end_time", default=None)

        if start is None or end is None:
            continue

        start_f = _round_seconds(start)
        end_f = _round_seconds(end)

        if end_f <= start_f:
            continue

        segments.append({
            "speech_region_id": str(_field(item, "speech_segment_id", "segment_id", "id", default=f"speech_{index:04d}")),
            "start_seconds": start_f,
            "end_seconds": end_f,
            "duration_seconds": _duration(start_f, end_f),
            "source": "speech_1_old_speech_segments",
        })

    return sorted(segments, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def merge_regions(
    regions: list[Mapping[str, Any]],
    *,
    max_gap_seconds: float = DEFAULT_MIN_SILENCE_SECONDS,
    min_region_seconds: float = 0.0,
    source: str = "merged",
) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []

    for item in regions:
        start = _round_seconds(_field(item, "start_seconds", "start", default=None))
        end = _round_seconds(_field(item, "end_seconds", "end", default=None))
        if end <= start:
            continue
        valid.append({
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": _duration(start, end),
        })

    valid.sort(key=lambda item: (item["start_seconds"], item["end_seconds"]))

    merged: list[dict[str, Any]] = []
    for item in valid:
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
            "speech_region_id": f"speech_region_{index:04d}",
            "start_seconds": _round_seconds(item["start_seconds"]),
            "end_seconds": _round_seconds(item["end_seconds"]),
            "duration_seconds": _duration(item["start_seconds"], item["end_seconds"]),
            "source": source,
        })

    return final


def word_derived_speech_regions(
    words: list[Mapping[str, Any]],
    *,
    merge_gap_seconds: float = 0.15,
) -> list[dict[str, Any]]:
    raw_regions = [
        {
            "start_seconds": _safe_float(word.get("start_seconds")),
            "end_seconds": _safe_float(word.get("end_seconds")),
        }
        for word in words
    ]

    return merge_regions(
        raw_regions,
        max_gap_seconds=merge_gap_seconds,
        min_region_seconds=0.0,
        source="word_complement_polluted_by_stretched_words",
    )


def invert_regions_to_silence_gaps(
    speech_regions: list[Mapping[str, Any]],
    *,
    media_duration_seconds: float,
    min_silence_seconds: float = 0.05,
    source: str = "vad",
) -> list[dict[str, Any]]:
    media_end = _round_seconds(media_duration_seconds)
    merged = merge_regions(
        list(speech_regions),
        max_gap_seconds=0.0,
        min_region_seconds=0.0,
        source="tmp",
    )

    gaps: list[dict[str, Any]] = []
    cursor = 0.0

    for region in merged:
        start = _round_seconds(region["start_seconds"])
        end = _round_seconds(region["end_seconds"])

        if start > cursor:
            duration = _duration(cursor, start)
            if duration >= min_silence_seconds:
                gaps.append({
                    "silence_gap_id": f"silence_gap_{len(gaps) + 1:04d}",
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
                "silence_gap_id": f"silence_gap_{len(gaps) + 1:04d}",
                "start_seconds": _round_seconds(cursor),
                "end_seconds": media_end,
                "duration_seconds": duration,
                "source": source,
            })

    return gaps


def silence_total_seconds(gaps: list[Mapping[str, Any]]) -> float:
    return round(sum(_safe_float(item.get("duration_seconds")) for item in gaps), 3)


def speech_share_percent_from_silence(
    *,
    media_duration_seconds: float,
    silence_seconds: float,
) -> float:
    if media_duration_seconds <= 0:
        return 0.0
    speech = max(0.0, media_duration_seconds - silence_seconds)
    return round((speech / media_duration_seconds) * 100.0, 3)


def build_energy_frame_scores_from_pcm_i16(
    samples: Sequence[int],
    *,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    frame_seconds: float = DEFAULT_FRAME_SECONDS,
) -> list[dict[str, Any]]:
    frame_size = max(1, int(sample_rate * frame_seconds))
    total = len(samples)
    frames: list[dict[str, Any]] = []

    for frame_index, start_sample in enumerate(range(0, total, frame_size)):
        end_sample = min(total, start_sample + frame_size)
        if end_sample <= start_sample:
            continue

        sq_sum = 0.0
        peak = 0.0
        count = end_sample - start_sample

        for idx in range(start_sample, end_sample):
            value = float(samples[idx]) / 32768.0
            abs_value = abs(value)
            sq_sum += value * value
            if abs_value > peak:
                peak = abs_value

        rms = math.sqrt(sq_sum / max(1, count))
        db = 20.0 * math.log10(max(rms, 1e-8))

        start_seconds = start_sample / sample_rate
        end_seconds = end_sample / sample_rate

        frames.append({
            "frame_index": frame_index,
            "start_seconds": round(start_seconds, 3),
            "end_seconds": round(end_seconds, 3),
            "rms": round(rms, 8),
            "peak": round(peak, 8),
            "db": round(db, 3),
        })

    return frames


def adaptive_energy_threshold_db(frames: list[Mapping[str, Any]]) -> dict[str, Any]:
    db_values = [_safe_float(item.get("db"), -120.0) for item in frames]
    voiced_candidates = [value for value in db_values if value > -80.0]

    if not voiced_candidates:
        return {
            "threshold_db": -40.0,
            "db_p20": -80.0,
            "db_p50": -60.0,
            "db_p75": -45.0,
            "db_p90": -35.0,
            "source": "fallback_no_voiced_candidates",
        }

    p20 = percentile(voiced_candidates, 20, default=-70.0)
    p50 = percentile(voiced_candidates, 50, default=-55.0)
    p75 = percentile(voiced_candidates, 75, default=-40.0)
    p90 = percentile(voiced_candidates, 90, default=-30.0)

    threshold = max(p20 + 9.0, p50 + 2.5)
    threshold = min(threshold, p75)

    return {
        "threshold_db": round(threshold, 3),
        "db_p20": round(p20, 3),
        "db_p50": round(p50, 3),
        "db_p75": round(p75, 3),
        "db_p90": round(p90, 3),
        "source": "adaptive_energy_percentiles",
    }


def vad_regions_from_frame_scores(
    frames: list[Mapping[str, Any]],
    *,
    threshold_db: float,
    min_speech_seconds: float = DEFAULT_MIN_SPEECH_SECONDS,
    min_silence_seconds: float = DEFAULT_MIN_SILENCE_SECONDS,
    speech_pad_seconds: float = DEFAULT_SPEECH_PAD_SECONDS,
    media_duration_seconds: float,
    source: str = "energy_vad_fallback",
) -> list[dict[str, Any]]:
    raw_regions: list[dict[str, Any]] = []
    in_speech = False
    start = 0.0
    last_end = 0.0

    for frame in frames:
        frame_start = _safe_float(frame.get("start_seconds"))
        frame_end = _safe_float(frame.get("end_seconds"))
        db = _safe_float(frame.get("db"), -120.0)
        is_speech = db >= threshold_db

        if is_speech and not in_speech:
            start = frame_start
            in_speech = True

        if not is_speech and in_speech:
            raw_regions.append({
                "start_seconds": start,
                "end_seconds": frame_start,
            })
            in_speech = False

        last_end = frame_end

    if in_speech:
        raw_regions.append({
            "start_seconds": start,
            "end_seconds": last_end,
        })

    padded: list[dict[str, Any]] = []
    media_end = _round_seconds(media_duration_seconds)

    for item in raw_regions:
        start_f = max(0.0, _safe_float(item["start_seconds"]) - speech_pad_seconds)
        end_f = min(media_end, _safe_float(item["end_seconds"]) + speech_pad_seconds)
        if end_f <= start_f:
            continue
        padded.append({
            "start_seconds": start_f,
            "end_seconds": end_f,
        })

    return merge_regions(
        padded,
        max_gap_seconds=min_silence_seconds,
        min_region_seconds=min_speech_seconds,
        source=source,
    )


def find_pollution_examples(
    *,
    vad_silence_gaps: list[Mapping[str, Any]],
    word_derived_silence_gaps: list[Mapping[str, Any]],
    words: list[Mapping[str, Any]],
    min_word_duration_seconds: float = 1.2,
    min_vad_gap_seconds: float = 0.8,
    max_word_gap_cover_ratio: float = 0.25,
    limit: int = 5,
) -> list[dict[str, Any]]:
    long_words = [
        word for word in words
        if _safe_float(word.get("duration_seconds")) >= min_word_duration_seconds
    ]

    examples: list[dict[str, Any]] = []

    for gap in vad_silence_gaps:
        gap_start = _safe_float(gap.get("start_seconds"))
        gap_end = _safe_float(gap.get("end_seconds"))
        gap_duration = _duration(gap_start, gap_end)

        if gap_duration < min_vad_gap_seconds:
            continue

        old_overlap = sum(
            _overlap_seconds(
                gap_start,
                gap_end,
                _safe_float(old.get("start_seconds")),
                _safe_float(old.get("end_seconds")),
            )
            for old in word_derived_silence_gaps
        )
        old_cover_ratio = old_overlap / max(0.001, gap_duration)

        if old_cover_ratio > max_word_gap_cover_ratio:
            continue

        best_word = None
        best_overlap = 0.0

        for word in long_words:
            overlap = _overlap_seconds(
                gap_start,
                gap_end,
                _safe_float(word.get("start_seconds")),
                _safe_float(word.get("end_seconds")),
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_word = word

        if best_word is None or best_overlap < min(0.5, gap_duration * 0.50):
            continue

        examples.append({
            "vad_silence_start_seconds": round(gap_start, 3),
            "vad_silence_end_seconds": round(gap_end, 3),
            "vad_silence_duration_seconds": gap_duration,
            "word_derived_silence_overlap_seconds": round(old_overlap, 3),
            "word_derived_cover_ratio": round(old_cover_ratio, 4),
            "polluting_word": {
                "word": best_word.get("word"),
                "start_seconds": best_word.get("start_seconds"),
                "end_seconds": best_word.get("end_seconds"),
                "duration_seconds": best_word.get("duration_seconds"),
            },
            "polluting_word_overlap_seconds": round(best_overlap, 3),
            "reason": "vad_found_silence_hidden_by_stretched_whisperx_word",
        })

    examples.sort(
        key=lambda item: (
            item["polluting_word_overlap_seconds"],
            item["vad_silence_duration_seconds"],
        ),
        reverse=True,
    )
    return examples[:limit]
