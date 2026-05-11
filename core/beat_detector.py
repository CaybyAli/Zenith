from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
from typing import Any, Iterable

from models.beat_detection import BeatDetectionResult, BeatPoint


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return minimum

    if not math.isfinite(value):
        return minimum

    return max(minimum, min(maximum, value))


def _safe_float_samples(samples: Iterable[float]) -> list[float]:
    safe_samples: list[float] = []

    try:
        iterator = iter(samples)
    except TypeError:
        return safe_samples

    for sample in iterator:
        try:
            value = float(sample)
        except (TypeError, ValueError):
            value = 0.0

        if not math.isfinite(value):
            value = 0.0

        safe_samples.append(value)

    return safe_samples


def calculate_frame_energy(samples: Iterable[float]) -> float:
    safe_samples = _safe_float_samples(samples)

    if not safe_samples:
        return 0.0

    total = 0.0
    for sample in safe_samples:
        total += sample * sample

    return total / len(safe_samples)


def build_energy_envelope(
    samples: Iterable[float],
    sample_rate: int,
    frame_ms: float = 50.0,
    hop_ms: float = 25.0,
) -> list[dict[str, float | int]]:
    safe_samples = _safe_float_samples(samples)

    if not safe_samples:
        return []

    try:
        safe_sample_rate = int(sample_rate)
    except (TypeError, ValueError):
        safe_sample_rate = 0

    if safe_sample_rate <= 0:
        return []

    try:
        safe_frame_ms = float(frame_ms)
    except (TypeError, ValueError):
        safe_frame_ms = 50.0

    try:
        safe_hop_ms = float(hop_ms)
    except (TypeError, ValueError):
        safe_hop_ms = 25.0

    if safe_frame_ms <= 0:
        safe_frame_ms = 50.0

    if safe_hop_ms <= 0:
        safe_hop_ms = 25.0

    frame_size = max(1, int(round(safe_sample_rate * safe_frame_ms / 1000.0)))
    hop_size = max(1, int(round(safe_sample_rate * safe_hop_ms / 1000.0)))

    envelope: list[dict[str, float | int]] = []
    frame_index = 0
    start = 0

    while start < len(safe_samples):
        end = min(start + frame_size, len(safe_samples))
        frame = safe_samples[start:end]
        energy = calculate_frame_energy(frame)

        start_seconds = start / safe_sample_rate
        end_seconds = end / safe_sample_rate
        center_seconds = (start_seconds + end_seconds) / 2.0

        envelope.append(
            {
                "index": frame_index,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "center_seconds": center_seconds,
                "energy": energy,
            }
        )

        frame_index += 1
        start += hop_size

    return envelope


def _get_energy(point: dict[str, Any]) -> float:
    try:
        energy = float(point.get("energy", 0.0))
    except (TypeError, ValueError):
        energy = 0.0

    if not math.isfinite(energy):
        return 0.0

    return max(0.0, energy)


def detect_beat_candidates(
    energy_envelope: list[dict[str, Any]],
    peak_threshold: float = 1.35,
    local_window: int = 4,
) -> list[BeatPoint]:
    if not energy_envelope:
        return []

    try:
        safe_peak_threshold = float(peak_threshold)
    except (TypeError, ValueError):
        safe_peak_threshold = 1.35

    if safe_peak_threshold <= 0:
        safe_peak_threshold = 1.35

    try:
        safe_local_window = int(local_window)
    except (TypeError, ValueError):
        safe_local_window = 4

    safe_local_window = max(1, safe_local_window)

    energies = [_get_energy(point) for point in energy_envelope]
    beats: list[BeatPoint] = []

    for index, point in enumerate(energy_envelope):
        energy = energies[index]

        if energy <= 0:
            continue

        previous_energy = energies[index - 1] if index > 0 else 0.0
        next_energy = energies[index + 1] if index + 1 < len(energies) else 0.0

        local_start = max(0, index - safe_local_window)
        local_end = min(len(energies), index + safe_local_window + 1)

        neighbor_energies = [
            energies[neighbor_index]
            for neighbor_index in range(local_start, local_end)
            if neighbor_index != index
        ]

        if neighbor_energies:
            average_energy = sum(neighbor_energies) / len(neighbor_energies)
        else:
            average_energy = energy

        if average_energy <= 0:
            local_energy = energy
        else:
            local_energy = average_energy

        is_peak = (
            energy > average_energy * safe_peak_threshold
            and energy > previous_energy
            and energy >= next_energy
        )

        if not is_peak:
            continue

        ratio = energy / max(average_energy, 0.000001)
        strength = _clamp((ratio - safe_peak_threshold) / safe_peak_threshold)
        confidence = _clamp((ratio - 1.0) / safe_peak_threshold)

        try:
            time_seconds = float(point.get("center_seconds", 0.0))
        except (TypeError, ValueError):
            time_seconds = 0.0

        try:
            source_index = int(point.get("index", index))
        except (TypeError, ValueError):
            source_index = index

        beats.append(
            BeatPoint(
                time_seconds=max(0.0, time_seconds),
                strength=strength,
                confidence=confidence,
                energy=energy,
                local_energy=local_energy,
                average_energy=average_energy,
                source_index=source_index,
                reason="local_energy_peak",
            )
        )

    return beats


def filter_beats_by_min_distance(
    beats: Iterable[BeatPoint],
    min_beat_distance_seconds: float = 0.25,
) -> list[BeatPoint]:
    try:
        safe_min_distance = float(min_beat_distance_seconds)
    except (TypeError, ValueError):
        safe_min_distance = 0.25

    if safe_min_distance < 0:
        safe_min_distance = 0.25

    sorted_beats = sorted(
        [beat for beat in beats if isinstance(beat, BeatPoint)],
        key=lambda beat: beat.time_seconds,
    )

    if not sorted_beats:
        return []

    filtered: list[BeatPoint] = []

    for beat in sorted_beats:
        if not filtered:
            filtered.append(beat)
            continue

        previous = filtered[-1]
        distance = beat.time_seconds - previous.time_seconds

        if distance < safe_min_distance:
            previous_score = (previous.strength, previous.confidence, previous.energy)
            current_score = (beat.strength, beat.confidence, beat.energy)

            if current_score > previous_score:
                filtered[-1] = beat
        else:
            filtered.append(beat)

    return sorted(filtered, key=lambda beat: beat.time_seconds)


def _average_interval_from_beats(beats: Iterable[BeatPoint]) -> float | None:
    sorted_beats = sorted(
        [beat for beat in beats if isinstance(beat, BeatPoint)],
        key=lambda beat: beat.time_seconds,
    )

    if len(sorted_beats) < 2:
        return None

    intervals: list[float] = []

    for index in range(1, len(sorted_beats)):
        interval = sorted_beats[index].time_seconds - sorted_beats[index - 1].time_seconds
        if interval > 0:
            intervals.append(interval)

    if not intervals:
        return None

    return sum(intervals) / len(intervals)


def estimate_bpm_from_beats(beats: Iterable[BeatPoint]) -> float | None:
    average_interval = _average_interval_from_beats(beats)

    if average_interval is None or average_interval <= 0:
        return None

    bpm = 60.0 / average_interval

    if 40.0 <= bpm <= 240.0:
        return round(bpm, 2)

    return None


def detect_beats_from_samples(
    samples: Iterable[float],
    sample_rate: int,
    channels: int = 1,
    frame_ms: float = 50.0,
    hop_ms: float = 25.0,
    peak_threshold: float = 1.35,
    min_beat_distance_seconds: float = 0.25,
    metadata: dict[str, Any] | None = None,
) -> BeatDetectionResult:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    warnings: list[str] = []
    errors: list[str] = []

    safe_samples = _safe_float_samples(samples)

    try:
        safe_sample_rate = int(sample_rate)
    except (TypeError, ValueError):
        safe_sample_rate = 0

    try:
        safe_channels = int(channels)
    except (TypeError, ValueError):
        safe_channels = 1

    if safe_channels <= 0:
        safe_channels = 1

    duration_seconds = 0.0
    if safe_sample_rate > 0 and safe_samples:
        duration_seconds = len(safe_samples) / safe_sample_rate

    if safe_sample_rate <= 0:
        errors.append("invalid_sample_rate")
        return BeatDetectionResult(
            status="failed",
            beats=[],
            beat_count=0,
            duration_seconds=duration_seconds,
            sample_rate=sample_rate if isinstance(sample_rate, int) else None,
            channels=safe_channels,
            energy_frame_count=0,
            peak_threshold=peak_threshold,
            min_beat_distance_seconds=min_beat_distance_seconds,
            warnings=warnings,
            errors=errors,
            metadata=safe_metadata,
        )

    if not safe_samples:
        warnings.append("empty_samples")
        return BeatDetectionResult(
            status="completed_with_warnings",
            beats=[],
            beat_count=0,
            estimated_bpm=None,
            average_beat_interval_seconds=None,
            duration_seconds=0.0,
            sample_rate=safe_sample_rate,
            channels=safe_channels,
            energy_frame_count=0,
            peak_threshold=peak_threshold,
            min_beat_distance_seconds=min_beat_distance_seconds,
            warnings=warnings,
            errors=errors,
            metadata=safe_metadata,
        )

    energy_envelope = build_energy_envelope(
        safe_samples,
        safe_sample_rate,
        frame_ms=frame_ms,
        hop_ms=hop_ms,
    )

    beat_candidates = detect_beat_candidates(
        energy_envelope,
        peak_threshold=peak_threshold,
        local_window=4,
    )

    beats = filter_beats_by_min_distance(
        beat_candidates,
        min_beat_distance_seconds=min_beat_distance_seconds,
    )

    estimated_bpm = estimate_bpm_from_beats(beats)
    average_interval = _average_interval_from_beats(beats)

    for beat in beats:
        beat.bpm_context = estimated_bpm

    if not beats:
        warnings.append("no_beats_detected")

    status = "ok" if not warnings and not errors else "completed_with_warnings"

    return BeatDetectionResult(
        status=status,
        beats=beats,
        beat_count=len(beats),
        estimated_bpm=estimated_bpm,
        average_beat_interval_seconds=average_interval,
        duration_seconds=duration_seconds,
        sample_rate=safe_sample_rate,
        channels=safe_channels,
        energy_frame_count=len(energy_envelope),
        peak_threshold=peak_threshold,
        min_beat_distance_seconds=min_beat_distance_seconds,
        warnings=warnings,
        errors=errors,
        metadata=safe_metadata,
    )


def _read_wav_samples_16bit(wav_path: Path) -> tuple[list[float], int, int]:
    with wave.open(str(wav_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()

        if sample_width != 2:
            raise ValueError("unsupported_wav_sample_width")

        raw_frames = wav_file.readframes(frame_count)

    if not raw_frames:
        return [], sample_rate, channels

    total_values = len(raw_frames) // 2
    unpack_format = "<" + ("h" * total_values)
    pcm_values = struct.unpack(unpack_format, raw_frames[: total_values * 2])

    samples: list[float] = []

    if channels <= 1:
        for value in pcm_values:
            samples.append(max(-1.0, min(1.0, value / 32768.0)))
        return samples, sample_rate, channels

    usable_value_count = len(pcm_values) - (len(pcm_values) % channels)

    for index in range(0, usable_value_count, channels):
        frame_values = pcm_values[index : index + channels]
        mixed = sum(frame_values) / channels
        samples.append(max(-1.0, min(1.0, mixed / 32768.0)))

    return samples, sample_rate, channels


def analyze_wav_beats(
    wav_path: str | Path,
    frame_ms: float = 50.0,
    hop_ms: float = 25.0,
    peak_threshold: float = 1.35,
    min_beat_distance_seconds: float = 0.25,
    metadata: dict[str, Any] | None = None,
) -> BeatDetectionResult:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    try:
        path = Path(wav_path)
    except TypeError:
        return BeatDetectionResult(
            status="failed",
            input_path=None,
            warnings=[],
            errors=["invalid_wav_path"],
            metadata=safe_metadata,
        )

    if path.suffix.lower() != ".wav":
        return BeatDetectionResult(
            status="failed",
            input_path=str(path),
            warnings=[],
            errors=["unsupported_wav_file_type"],
            metadata=safe_metadata,
        )

    if not path.exists():
        return BeatDetectionResult(
            status="failed",
            input_path=str(path),
            warnings=[],
            errors=["wav_file_missing"],
            metadata=safe_metadata,
        )

    try:
        samples, sample_rate, channels = _read_wav_samples_16bit(path)
    except Exception as exc:
        return BeatDetectionResult(
            status="failed",
            input_path=str(path),
            warnings=[],
            errors=["wav_read_failed"],
            metadata={
                **safe_metadata,
                "error_detail": str(exc),
            },
        )

    result = detect_beats_from_samples(
        samples=samples,
        sample_rate=sample_rate,
        channels=channels,
        frame_ms=frame_ms,
        hop_ms=hop_ms,
        peak_threshold=peak_threshold,
        min_beat_distance_seconds=min_beat_distance_seconds,
        metadata=safe_metadata,
    )

    result.input_path = str(path)
    return result
