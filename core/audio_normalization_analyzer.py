from __future__ import annotations

import math
import os
import struct
import wave
from typing import Any, Iterable

from models.audio_normalization import AudioLevelStats, AudioNormalizationResult


def calculate_rms(samples: Iterable[float]) -> float:
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


def dbfs_from_amplitude(amplitude: float) -> float | None:
    try:
        a = float(amplitude)
    except (TypeError, ValueError):
        return None
    if a <= 0.0:
        return None
    return 20.0 * math.log10(a)


def clamp_gain_to_peak_headroom(
    recommended_gain_db: float,
    peak_dbfs: float | None,
    target_peak_dbfs: float = -1.0,
) -> tuple[float, bool]:
    if peak_dbfs is None:
        return recommended_gain_db, False
    max_allowed_gain = target_peak_dbfs - peak_dbfs
    if recommended_gain_db > max_allowed_gain:
        return max_allowed_gain, True
    return recommended_gain_db, False


def analyze_audio_samples(
    samples: Iterable[float],
    sample_rate: int | None = None,
    channels: int | None = None,
    clipping_threshold: float = 0.999,
    metadata: dict[str, Any] | None = None,
) -> AudioLevelStats:
    warnings: list[str] = []
    errors: list[str] = []
    out_of_range_found = False

    cleaned: list[float] = []
    for s in samples:
        if s is None:
            continue
        try:
            v = float(s)
        except (TypeError, ValueError):
            continue
        if v < -1.0 or v > 1.0:
            out_of_range_found = True
            v = max(-1.0, min(1.0, v))
        cleaned.append(v)

    if out_of_range_found:
        warnings.append("samples_out_of_range")

    sample_count = len(cleaned)

    if sample_count == 0:
        warnings.append("no_samples")
        return AudioLevelStats(
            sample_count=0,
            warnings=warnings,
            errors=errors,
            metadata=dict(metadata or {}),
        )

    peak_amplitude = max(abs(v) for v in cleaned)
    rms = calculate_rms(cleaned)
    peak_dbfs = dbfs_from_amplitude(peak_amplitude)
    rms_dbfs = dbfs_from_amplitude(rms)

    headroom_db: float | None = None
    if peak_dbfs is not None:
        headroom_db = 0.0 - peak_dbfs

    dynamic_range_db: float | None = None
    if peak_dbfs is not None and rms_dbfs is not None:
        dynamic_range_db = peak_dbfs - rms_dbfs

    clipping_sample_count = sum(1 for v in cleaned if abs(v) >= clipping_threshold)
    clipping_ratio = clipping_sample_count / sample_count

    if clipping_sample_count > 0:
        warnings.append("clipping_detected")

    valid_rate = isinstance(sample_rate, int) and sample_rate > 0
    valid_channels = isinstance(channels, int) and channels > 0

    if valid_rate and valid_channels:
        duration_seconds = sample_count / sample_rate / channels
    else:
        duration_seconds = 0.0

    if sample_rate is not None and not valid_rate:
        warnings.append("invalid_sample_rate")
    if channels is not None and not valid_channels:
        warnings.append("invalid_channels")

    return AudioLevelStats(
        peak_amplitude=peak_amplitude,
        rms=rms,
        peak_dbfs=peak_dbfs,
        rms_dbfs=rms_dbfs,
        headroom_db=headroom_db,
        dynamic_range_db=dynamic_range_db,
        clipping_sample_count=clipping_sample_count,
        clipping_ratio=clipping_ratio,
        sample_count=sample_count,
        duration_seconds=duration_seconds,
        sample_rate=sample_rate if valid_rate else None,
        channels=channels if valid_channels else None,
        warnings=warnings,
        errors=errors,
        metadata=dict(metadata or {}),
    )


def build_normalization_result_from_stats(
    stats: AudioLevelStats,
    input_path: str | None = None,
    target_rms_dbfs: float = -18.0,
    target_peak_dbfs: float = -1.0,
    quiet_threshold_dbfs: float = -24.0,
    loud_threshold_dbfs: float = -10.0,
    metadata: dict[str, Any] | None = None,
) -> AudioNormalizationResult:
    warnings: list[str] = list(stats.warnings)
    errors: list[str] = list(stats.errors)

    if stats.sample_count == 0:
        if "no_samples" not in warnings:
            warnings.append("no_samples")
        return AudioNormalizationResult(
            status="completed_with_warnings",
            input_path=input_path,
            level_status="unknown",
            stats=stats,
            target_rms_dbfs=target_rms_dbfs,
            target_peak_dbfs=target_peak_dbfs,
            recommendation="retry_or_fix_audio",
            warnings=warnings,
            errors=errors,
            metadata=dict(metadata or {}),
        )

    if stats.rms == 0.0:
        status = "completed_with_warnings" if warnings else "ok"
        return AudioNormalizationResult(
            status=status,
            input_path=input_path,
            level_status="silent",
            stats=stats,
            target_rms_dbfs=target_rms_dbfs,
            target_peak_dbfs=target_peak_dbfs,
            normalization_needed=False,
            recommendation="audio_silent",
            warnings=warnings,
            errors=errors,
            metadata=dict(metadata or {}),
        )

    rms_dbfs = stats.rms_dbfs
    peak_dbfs = stats.peak_dbfs

    recommended_gain_db = 0.0
    limited_gain_db = 0.0
    gain_limited_by_peak = False
    normalization_needed = False
    level_status = "normal"
    recommendation = "no_normalization_needed"

    if stats.clipping_sample_count > 0:
        level_status = "clipped"
        recommendation = "fix_clipping"
        normalization_needed = True
        recommended_gain_db = 0.0
        limited_gain_db = 0.0
        gain_limited_by_peak = False

    elif rms_dbfs is not None and rms_dbfs < quiet_threshold_dbfs:
        level_status = "too_quiet"
        recommended_gain_db = target_rms_dbfs - rms_dbfs
        limited_gain_db, gain_limited_by_peak = clamp_gain_to_peak_headroom(
            recommended_gain_db, peak_dbfs, target_peak_dbfs
        )
        normalization_needed = True
        recommendation = "apply_gain"

    elif rms_dbfs is not None and rms_dbfs > loud_threshold_dbfs:
        level_status = "too_loud"
        recommended_gain_db = target_rms_dbfs - rms_dbfs
        limited_gain_db = recommended_gain_db
        gain_limited_by_peak = False
        normalization_needed = True
        recommendation = "reduce_gain"

    else:
        level_status = "normal"
        recommended_gain_db = target_rms_dbfs - rms_dbfs if rms_dbfs is not None else 0.0
        limited_gain_db, gain_limited_by_peak = clamp_gain_to_peak_headroom(
            recommended_gain_db, peak_dbfs, target_peak_dbfs
        )
        if abs(recommended_gain_db) < 1.0:
            normalization_needed = False
            recommendation = "no_normalization_needed"
        else:
            normalization_needed = True
            recommendation = "apply_gain" if recommended_gain_db > 0 else "reduce_gain"

    would_clip_after_gain = False
    if peak_dbfs is not None:
        would_clip_after_gain = (peak_dbfs + limited_gain_db) > target_peak_dbfs

    status = "completed_with_warnings" if warnings else "ok"

    return AudioNormalizationResult(
        status=status,
        input_path=input_path,
        level_status=level_status,
        stats=stats,
        target_rms_dbfs=target_rms_dbfs,
        target_peak_dbfs=target_peak_dbfs,
        recommended_gain_db=recommended_gain_db,
        limited_gain_db=limited_gain_db,
        gain_limited_by_peak=gain_limited_by_peak,
        would_clip_after_gain=would_clip_after_gain,
        normalization_needed=normalization_needed,
        recommendation=recommendation,
        warnings=warnings,
        errors=errors,
        metadata=dict(metadata or {}),
    )


def analyze_wav_audio_normalization(
    wav_path: str,
    target_rms_dbfs: float = -18.0,
    target_peak_dbfs: float = -1.0,
    clipping_threshold: float = 0.999,
    metadata: dict[str, Any] | None = None,
) -> AudioNormalizationResult:
    if not os.path.exists(wav_path):
        return AudioNormalizationResult(
            status="failed",
            input_path=wav_path,
            target_rms_dbfs=target_rms_dbfs,
            target_peak_dbfs=target_peak_dbfs,
            errors=["wav_file_missing"],
        )

    if not wav_path.lower().endswith(".wav"):
        return AudioNormalizationResult(
            status="failed",
            input_path=wav_path,
            target_rms_dbfs=target_rms_dbfs,
            target_peak_dbfs=target_peak_dbfs,
            errors=["unsupported_audio_format"],
        )

    try:
        with wave.open(wav_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            raw_data = wf.readframes(n_frames)
    except Exception as exc:
        return AudioNormalizationResult(
            status="failed",
            input_path=wav_path,
            target_rms_dbfs=target_rms_dbfs,
            target_peak_dbfs=target_peak_dbfs,
            errors=[f"wav_read_failed: {exc}"],
        )

    try:
        if sample_width == 1:
            raw_samples = struct.unpack(f"{n_frames * n_channels}B", raw_data)
            norm_factor = 128.0
            samples: list[float] = [(s - 128) / norm_factor for s in raw_samples]
        elif sample_width == 2:
            raw_samples = struct.unpack(f"<{n_frames * n_channels}h", raw_data)
            norm_factor = 32768.0
            samples = [s / norm_factor for s in raw_samples]
        elif sample_width == 4:
            raw_samples = struct.unpack(f"<{n_frames * n_channels}i", raw_data)
            norm_factor = 2147483648.0
            samples = [s / norm_factor for s in raw_samples]
        else:
            return AudioNormalizationResult(
                status="failed",
                input_path=wav_path,
                target_rms_dbfs=target_rms_dbfs,
                target_peak_dbfs=target_peak_dbfs,
                errors=[f"unsupported_sample_width: {sample_width}"],
            )
    except Exception as exc:
        return AudioNormalizationResult(
            status="failed",
            input_path=wav_path,
            target_rms_dbfs=target_rms_dbfs,
            target_peak_dbfs=target_peak_dbfs,
            errors=[f"wav_read_failed: {exc}"],
        )

    stats = analyze_audio_samples(
        samples=samples,
        sample_rate=sample_rate,
        channels=n_channels,
        clipping_threshold=clipping_threshold,
        metadata=metadata,
    )

    return build_normalization_result_from_stats(
        stats=stats,
        input_path=wav_path,
        target_rms_dbfs=target_rms_dbfs,
        target_peak_dbfs=target_peak_dbfs,
        metadata=metadata,
    )
