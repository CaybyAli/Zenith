from __future__ import annotations

import math
import wave
from array import array
from pathlib import Path
from typing import Any


GAMEPLAY_ZOOM = 1.4
ZOOM_PAD_SECONDS = 0.05
SUBWINDOW_SECONDS = 0.1
SILENCE_FLOOR_PERCENTILE = 20.0
LONG_WORD_SECONDS = 1.5
LONG_WORD_DROP_DB = 6.0
INSTANT_MAX_WORD_SECONDS = 0.6
INSTANT_MAX_TOTAL_SECONDS = 1.5


def refine_friend_reaction_candidates(
    candidates: list[dict[str, Any]],
    friend_segments: Any,
    a2_audio_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    segments_by_index = _source_segments_by_index(friend_segments)
    word_annotated = _annotate_word_boundaries(candidates, segments_by_index, a2_audio_path)
    return _annotate_presence_gate(word_annotated, a2_audio_path)


def _source_segments_by_index(friend_segments: Any) -> dict[int, dict[str, Any]]:
    if isinstance(friend_segments, dict):
        segments = friend_segments.get("segments")
    else:
        segments = friend_segments

    if not isinstance(segments, list):
        raise RuntimeError("Friend segments input has no segments list")

    by_index: dict[int, dict[str, Any]] = {}
    missing_word_timestamps = 0
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue
        words = segment.get("words")
        if not isinstance(words, list) or not words:
            missing_word_timestamps += 1
        else:
            for word in words:
                if not isinstance(word, dict) or word.get("start") is None or word.get("end") is None:
                    missing_word_timestamps += 1
                    break
        by_index[index] = segment

    if missing_word_timestamps:
        raise RuntimeError(
            f"Friend segments input has {missing_word_timestamps} segment(s) "
            "without word-level start/end timestamps"
        )
    return by_index


def _word_boundaries_for_row(
    row: dict[str, Any],
    segments_by_index: dict[int, dict[str, Any]],
    a2_audio_path: Path,
) -> dict[str, Any]:
    source_index = row.get("source_index")
    if not isinstance(source_index, int):
        raise RuntimeError(f"Candidate has no integer source_index: {row.get('friend_text')}")
    segment = segments_by_index.get(source_index)
    if not isinstance(segment, dict):
        raise RuntimeError(f"No friend segment for source_index={source_index}")

    raw_words = segment.get("words")
    if not isinstance(raw_words, list) or not raw_words:
        raise RuntimeError(f"Friend segment source_index={source_index} has no words[]")

    words: list[dict[str, Any]] = []
    for raw_word in raw_words:
        if not isinstance(raw_word, dict):
            continue
        try:
            start = float(raw_word["start"])
            end = float(raw_word["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if end < start:
            continue
        word = str(raw_word.get("word") or "")
        duration = end - start
        item = {
            "word": word,
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(duration, 3),
        }
        words.append(item)

    if not words:
        raise RuntimeError(f"Friend segment source_index={source_index} has no usable word timestamps")

    first_word_start = float(words[0]["start"])
    last_word = words[-1]
    validation = _energy_validated_long_word_end(last_word, a2_audio_path)
    last_word_end = float(validation["energy_validated_end"])

    max_word_dur = max(float(word["duration"]) for word in words)
    total_dur = max(0.0, last_word_end - first_word_start)
    zoom_mode = (
        "instant"
        if max_word_dur < INSTANT_MAX_WORD_SECONDS and total_dur <= INSTANT_MAX_TOTAL_SECONDS
        else "smooth"
    )
    zoom_start = max(0.0, first_word_start - ZOOM_PAD_SECONDS)
    zoom_end = max(zoom_start, last_word_end + ZOOM_PAD_SECONDS)

    return {
        "first_word_start": round(first_word_start, 3),
        "last_word_end": round(last_word_end, 3),
        "max_word_dur": round(max_word_dur, 3),
        "total_dur": round(total_dur, 3),
        "zoom_mode": zoom_mode,
        "zoom_mode_reason": (
            "short_sharp_word_character"
            if zoom_mode == "instant"
            else "held_word_or_long_sentence_word_character"
        ),
        "zoom_start": round(zoom_start, 3),
        "zoom_end": round(zoom_end, 3),
        "zoom_dauer": round(zoom_end - zoom_start, 3),
        "words": words,
        "energie_voice_end": round(last_word_end, 3),
        "energy_validated_last_word": validation,
    }


def _annotate_word_boundaries(
    rows: list[dict[str, Any]],
    segments_by_index: dict[int, dict[str, Any]],
    a2_audio_path: Path,
) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for row in rows:
        segment_bounds: dict[str, float] = {}
        if row.get("zoom_start") is not None and row.get("zoom_end") is not None:
            segment_bounds = {
                "segment_zoom_start": round(float(row["zoom_start"]), 3),
                "segment_zoom_end": round(float(row["zoom_end"]), 3),
            }
        word_bounds = _word_boundaries_for_row(row, segments_by_index, a2_audio_path)
        annotated.append(
            {
                **row,
                **segment_bounds,
                **word_bounds,
            }
        )
    return annotated


def _energy_validated_long_word_end(word: dict[str, Any], a2_audio_path: Path) -> dict[str, Any]:
    start = float(word["start"])
    end = float(word["end"])
    measurement = _measure_track2_window(a2_audio_path, start, end)
    subwindows = list(measurement.get("subwindows") or [])
    word_peak_rms = max((float(item["rms_db"]) for item in subwindows), default=-120.0)
    threshold = word_peak_rms - LONG_WORD_DROP_DB
    voiced = [
        item for item in subwindows
        if float(item["rms_db"]) > threshold
    ]
    energy_end = float(voiced[-1]["end"]) if voiced else start
    energy_end = min(end, max(start, energy_end))
    return {
        "word": str(word.get("word") or ""),
        "start": round(start, 3),
        "raw_end": round(end, 3),
        "duration": round(end - start, 3),
        "word_peak_rms": round(word_peak_rms, 3),
        "threshold_db": round(threshold, 3),
        "energy_validated_end": round(energy_end, 3),
        "clamped": energy_end < end - 0.001,
    }


def _dbfs_from_rms(rms: float, full_scale: float) -> float:
    if rms <= 0.0 or full_scale <= 0.0:
        return -120.0
    return 20.0 * math.log10(rms / full_scale)


def _decode_pcm_samples(raw: bytes, sample_width: int) -> tuple[list[int], float]:
    if sample_width == 1:
        return [int(value) - 128 for value in raw], 128.0

    if sample_width == 2:
        samples = array("h")
        samples.frombytes(raw)
        return list(samples), 32768.0

    if sample_width == 3:
        samples = []
        for offset in range(0, len(raw) - 2, 3):
            value = int.from_bytes(raw[offset:offset + 3], byteorder="little", signed=False)
            if value & 0x800000:
                value -= 0x1000000
            samples.append(value)
        return samples, float(1 << 23)

    if sample_width == 4:
        samples = array("i")
        samples.frombytes(raw)
        return list(samples), float(1 << 31)

    raise RuntimeError(f"Unsupported WAV sample width: {sample_width}")


def _rms_db_for_samples(samples: list[int], full_scale: float) -> float:
    if not samples:
        return -120.0
    square_sum = sum(float(sample) * float(sample) for sample in samples)
    rms = math.sqrt(square_sum / float(len(samples)))
    return _dbfs_from_rms(rms, full_scale)


def _measure_track2_window(a2_audio_path: Path, start: float, end: float) -> dict[str, Any]:
    wav_path = Path(a2_audio_path)
    if not wav_path.exists():
        raise RuntimeError(f"A2 audio WAV missing: {wav_path}")

    duration = max(0.001, end - start)

    with wave.open(str(wav_path), "rb") as wav:
        sample_rate = float(wav.getframerate())
        sample_width = int(wav.getsampwidth())
        channel_count = int(wav.getnchannels())
        start_frame = max(0, int(math.floor(start * sample_rate)))
        frame_count = max(1, int(math.ceil(duration * sample_rate)))
        start_frame = min(start_frame, max(0, wav.getnframes() - 1))
        frame_count = min(frame_count, wav.getnframes() - start_frame)
        wav.setpos(start_frame)
        raw = wav.readframes(frame_count)

    samples, full_scale = _decode_pcm_samples(raw, sample_width)
    overall_rms_db = _rms_db_for_samples(samples, full_scale)
    peak_abs = max((abs(sample) for sample in samples), default=0)
    peak_db = _dbfs_from_rms(float(peak_abs), full_scale)

    frames_per_window = max(1, int(round(sample_rate * SUBWINDOW_SECONDS)))
    samples_per_window = frames_per_window * max(1, channel_count)
    subwindows: list[dict[str, float]] = []
    for sample_offset in range(0, len(samples), samples_per_window):
        chunk = samples[sample_offset:sample_offset + samples_per_window]
        if not chunk:
            continue
        frame_offset = sample_offset / max(1, channel_count)
        window_start = start + (frame_offset / sample_rate)
        window_end = min(end, window_start + SUBWINDOW_SECONDS)
        rms_db = _rms_db_for_samples(chunk, full_scale)
        subwindows.append(
            {
                "start": round(window_start, 3),
                "end": round(window_end, 3),
                "rms_db": round(rms_db, 3),
            }
        )

    return {
        "friend_rms_db": overall_rms_db,
        "friend_peak_db": peak_db,
        "peak_sub_rms_db": max((float(item["rms_db"]) for item in subwindows), default=-120.0),
        "subwindow_seconds": SUBWINDOW_SECONDS,
        "subwindow_count": len(subwindows),
        "subwindows": subwindows,
    }


def _measure_friend_voice(row: dict[str, Any], a2_audio_path: Path) -> dict[str, Any]:
    return _measure_track2_window(a2_audio_path, float(row["start"]), float(row["end"]))


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        raise RuntimeError("Cannot compute percentile without values")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * max(0.0, min(100.0, float(percentile))) / 100.0
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] + ((ordered[upper] - ordered[lower]) * weight)


def _annotate_presence_gate(
    rows: list[dict[str, Any]],
    a2_audio_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    for row in rows:
        row.update(_measure_friend_voice(row, a2_audio_path))
        row["loudness_score_db"] = float(row["friend_rms_db"])

    peak_sub_values = [float(row["peak_sub_rms_db"]) for row in rows]
    silence_floor = _percentile(peak_sub_values, SILENCE_FLOOR_PERCENTILE)

    accepted: list[dict[str, Any]] = []
    rejected_silence: list[dict[str, Any]] = []
    for row in rows:
        peak_sub_rms_db = float(row["peak_sub_rms_db"])
        if peak_sub_rms_db < silence_floor:
            row["rejected_reason"] = "rejected_silence"
            row["silence_floor_db"] = round(silence_floor, 3)
            rejected_silence.append(row)
            continue

        row["silence_floor_db"] = round(silence_floor, 3)
        accepted.append(row)

    if not accepted:
        raise RuntimeError("All candidates rejected by adaptive voice-presence gate")

    policy = {
        "measurement_source": str(Path(a2_audio_path)),
        "metric": "100ms_subwindow_rms_dbfs_from_a2_audio_wav",
        "subwindow_seconds": SUBWINDOW_SECONDS,
        "silence_floor_percentile": SILENCE_FLOOR_PERCENTILE,
        "silence_floor_peak_sub_rms_db": round(silence_floor, 3),
        "presence_gate": "candidate_rejected_when_peak_100ms_subwindow_below_adaptive_silence_floor",
        "accepted_count": len(accepted),
        "rejected_silence_count": len(rejected_silence),
        "zoom_mode_source": (
            f"word_character instant=max_word_dur<{INSTANT_MAX_WORD_SECONDS:g} "
            f"and total_dur<={INSTANT_MAX_TOTAL_SECONDS:g}; smooth otherwise"
        ),
    }
    return accepted, rejected_silence, policy
