from __future__ import annotations

import math
import struct
import wave
from typing import Any

from models.rms_energy import RmsEnergyPoint, RmsEnergyTimelineResult

DEFAULT_FRAME_MS: float = 10.0
DEFAULT_HOP_MS: float = 5.0
DEFAULT_SILENCE_RMS_THRESHOLD: float = 0.001


def calculate_rms(samples: list[float]) -> float:
    if not samples:
        return 0.0
    total = 0.0
    count = 0
    for s in samples:
        try:
            v = float(s)
            total += v * v
            count += 1
        except (TypeError, ValueError):
            continue
    if count == 0:
        return 0.0
    return math.sqrt(total / count)


def normalize_values(values: list[float]) -> list[float]:
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    span = max_val - min_val
    if span == 0.0:
        if max_val > 0.0:
            return [1.0] * len(values)
        return [0.0] * len(values)
    return [(v - min_val) / span for v in values]


def dbfs_from_rms(rms: float) -> float | None:
    if rms <= 0.0:
        return None
    return 20.0 * math.log10(rms)


def build_rms_energy_timeline_from_samples(
    samples: list[float],
    sample_rate: int,
    frame_ms: float = DEFAULT_FRAME_MS,
    hop_ms: float = DEFAULT_HOP_MS,
    silence_rms_threshold: float = DEFAULT_SILENCE_RMS_THRESHOLD,
    source_path: str | None = None,
    channels: int | None = None,
) -> RmsEnergyTimelineResult:
    warnings: list[str] = []
    errors: list[str] = []

    if not isinstance(sample_rate, int) or sample_rate <= 0:
        return RmsEnergyTimelineResult(
            status="failed",
            source_path=source_path,
            channels=channels,
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            errors=["invalid_sample_rate"],
        )

    if not samples:
        duration = 0.0
        return RmsEnergyTimelineResult(
            status="ok",
            source_path=source_path,
            sample_rate=sample_rate,
            channels=channels,
            duration_seconds=duration,
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            points=[],
            point_count=0,
            warnings=["no_samples"],
        )

    duration_seconds = len(samples) / sample_rate

    frame_size = max(1, int(sample_rate * frame_ms / 1000.0))
    hop_size = max(1, int(sample_rate * hop_ms / 1000.0))

    total_samples = len(samples)

    raw_rms_values: list[float] = []
    frame_indices: list[tuple[int, int]] = []

    start_idx = 0
    while start_idx < total_samples:
        end_idx = min(start_idx + frame_size, total_samples)
        window = samples[start_idx:end_idx]
        rms_val = calculate_rms(window)
        raw_rms_values.append(rms_val)
        frame_indices.append((start_idx, end_idx))
        start_idx += hop_size

    normalized = normalize_values(raw_rms_values)

    points: list[RmsEnergyPoint] = []
    for i, (si, ei) in enumerate(frame_indices):
        rms_val = raw_rms_values[i]
        norm_val = normalized[i]
        start_sec = si / sample_rate
        end_sec = ei / sample_rate
        center_sec = (start_sec + end_sec) / 2.0
        point = RmsEnergyPoint(
            start_seconds=start_sec,
            end_seconds=end_sec,
            center_seconds=center_sec,
            rms=rms_val,
            normalized_energy=norm_val,
            dbfs=dbfs_from_rms(rms_val),
            sample_count=ei - si,
            is_silent=rms_val <= silence_rms_threshold,
        )
        points.append(point)

    if points:
        rms_vals = [p.rms for p in points]
        norm_vals = [p.normalized_energy for p in points]
        min_rms = min(rms_vals)
        max_rms = max(rms_vals)
        avg_rms = sum(rms_vals) / len(rms_vals)
        min_norm = min(norm_vals)
        max_norm = max(norm_vals)
        avg_norm = sum(norm_vals) / len(norm_vals)
    else:
        min_rms = max_rms = avg_rms = 0.0
        min_norm = max_norm = avg_norm = 0.0

    status = "completed_with_warnings" if warnings else "ok"

    return RmsEnergyTimelineResult(
        status=status,
        source_path=source_path,
        sample_rate=sample_rate,
        channels=channels,
        duration_seconds=duration_seconds,
        frame_ms=frame_ms,
        hop_ms=hop_ms,
        points=points,
        point_count=len(points),
        min_rms=min_rms,
        max_rms=max_rms,
        avg_rms=avg_rms,
        min_normalized_energy=min_norm,
        max_normalized_energy=max_norm,
        avg_normalized_energy=avg_norm,
        warnings=warnings,
        errors=errors,
    )


def analyze_wav_rms_energy(
    wav_path: str,
    frame_ms: float = DEFAULT_FRAME_MS,
    hop_ms: float = DEFAULT_HOP_MS,
    silence_rms_threshold: float = DEFAULT_SILENCE_RMS_THRESHOLD,
) -> RmsEnergyTimelineResult:
    import os

    if not os.path.exists(wav_path):
        return RmsEnergyTimelineResult(
            status="failed",
            source_path=wav_path,
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            errors=["wav_file_missing"],
        )

    try:
        with wave.open(wav_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            raw_data = wf.readframes(n_frames)
    except Exception as exc:
        return RmsEnergyTimelineResult(
            status="failed",
            source_path=wav_path,
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            errors=[f"wav_read_failed: {exc}"],
        )

    if sample_width == 2:
        fmt = f"<{n_frames * n_channels}h"
        try:
            raw_samples = struct.unpack(fmt, raw_data)
        except struct.error as exc:
            return RmsEnergyTimelineResult(
                status="failed",
                source_path=wav_path,
                sample_rate=sample_rate,
                channels=n_channels,
                frame_ms=frame_ms,
                hop_ms=hop_ms,
                errors=[f"wav_read_failed: {exc}"],
            )
        norm_factor = 32768.0
        if n_channels == 1:
            samples = [s / norm_factor for s in raw_samples]
        else:
            samples = []
            for i in range(0, len(raw_samples), n_channels):
                frame_vals = raw_samples[i : i + n_channels]
                samples.append(sum(frame_vals) / (n_channels * norm_factor))
    elif sample_width == 1:
        raw_samples_8 = struct.unpack(f"{n_frames * n_channels}B", raw_data)
        norm_factor = 128.0
        if n_channels == 1:
            samples = [(s - 128) / norm_factor for s in raw_samples_8]
        else:
            samples = []
            for i in range(0, len(raw_samples_8), n_channels):
                frame_vals = raw_samples_8[i : i + n_channels]
                avg = sum(v - 128 for v in frame_vals) / n_channels
                samples.append(avg / norm_factor)
    else:
        return RmsEnergyTimelineResult(
            status="failed",
            source_path=wav_path,
            sample_rate=sample_rate,
            channels=n_channels,
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            errors=[f"unsupported_sample_width: {sample_width}"],
        )

    return build_rms_energy_timeline_from_samples(
        samples=samples,
        sample_rate=sample_rate,
        frame_ms=frame_ms,
        hop_ms=hop_ms,
        silence_rms_threshold=silence_rms_threshold,
        source_path=wav_path,
        channels=n_channels,
    )
