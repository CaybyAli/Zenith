from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path


MAPPING_VERSION = "1"
_ALLOWED_CUT_REASONS = {"low_action", "dead_air", "unknown"}


@dataclass(frozen=True)
class KeptSegment:
    raw_start_s: float
    raw_end_s: float
    final_start_s: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CutSegment:
    raw_start_s: float
    raw_end_s: float
    cut_reason_class: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if payload["cut_reason_class"] not in _ALLOWED_CUT_REASONS:
            payload["cut_reason_class"] = "unknown"
        return payload


@dataclass(frozen=True)
class CutSelectionMap:
    pair_id: str
    raw_duration_seconds: float
    final_duration_seconds: float
    kept_segments: list[dict[str, Any]]
    cut_segments: list[dict[str, Any]]
    alignment_confidence: float
    mapping_version: str = MAPPING_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_cut_selection_map(
    pair_path: str | Path,
    *,
    raw_audio_path: str | Path | None = None,
    final_audio_path: str | Path | None = None,
    power_profile: str | None = None,
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
) -> dict[str, Any]:
    """
    Build a passive cut-selection map for one pair_NNN folder.

    power_profile is accepted as a hook for Phase 5 orchestration. This module
    is deterministic local DSP/FFmpeg work and currently does not need
    profile-specific flags.
    """

    pair_dir = Path(pair_path)
    pair_id = pair_dir.name

    raw_path = Path(raw_audio_path) if raw_audio_path else pair_dir / "raw_mixed_audio.mp4"
    final_path = Path(final_audio_path) if final_audio_path else pair_dir / "final.mp4"

    if not raw_path.exists():
        raise FileNotFoundError(f"Missing prepared raw audio input: {raw_path}")
    if not final_path.exists():
        raise FileNotFoundError(f"Missing final audio input: {final_path}")

    alignment = align_final_to_raw(
        raw_path,
        final_path,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
    )

    raw_duration = probe_media_duration_seconds(raw_path, ffprobe_path=ffprobe_path)
    final_duration = probe_media_duration_seconds(final_path, ffprobe_path=ffprobe_path)

    raw_start = clamp_seconds(alignment["raw_start_s"], minimum=0.0, maximum=raw_duration)
    raw_end = clamp_seconds(raw_start + final_duration, minimum=raw_start, maximum=raw_duration)

    kept = [
        KeptSegment(
            raw_start_s=round(raw_start, 3),
            raw_end_s=round(raw_end, 3),
            final_start_s=0.0,
        ).to_dict()
    ]

    cut_segments = build_cut_segments_from_kept(
        raw_duration_seconds=raw_duration,
        kept_segments=kept,
        raw_audio_path=raw_path,
        ffmpeg_path=ffmpeg_path,
    )

    return CutSelectionMap(
        pair_id=pair_id,
        raw_duration_seconds=round(raw_duration, 3),
        final_duration_seconds=round(final_duration, 3),
        kept_segments=kept,
        cut_segments=cut_segments,
        alignment_confidence=round(float(alignment["alignment_confidence"]), 6),
    ).to_dict()


def align_final_to_raw(
    raw_media_path: str | Path,
    final_media_path: str | Path,
    *,
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
) -> dict[str, float]:
    """
    Align final audio inside raw audio with deterministic STFT-envelope
    cross-correlation.

    Returns:
    - raw_start_s
    - alignment_confidence
    """

    raw_path = Path(raw_media_path)
    final_path = Path(final_media_path)

    raw_sample_rate = probe_audio_sample_rate(raw_path, ffprobe_path=ffprobe_path)
    final_sample_rate = probe_audio_sample_rate(final_path, ffprobe_path=ffprobe_path)
    target_sample_rate = min(raw_sample_rate, final_sample_rate)

    with tempfile.TemporaryDirectory(prefix="zenith_p5_2_align_") as temp_dir:
        temp_root = Path(temp_dir)
        raw_wav = temp_root / "raw.wav"
        final_wav = temp_root / "final.wav"

        extract_audio_to_wav(
            raw_path,
            raw_wav,
            sample_rate=target_sample_rate,
            ffmpeg_path=ffmpeg_path,
        )
        extract_audio_to_wav(
            final_path,
            final_wav,
            sample_rate=target_sample_rate,
            ffmpeg_path=ffmpeg_path,
        )

        raw_signal, sample_rate = read_wav_mono(raw_wav)
        final_signal, _ = read_wav_mono(final_wav)

    return align_signals_by_stft_envelope(
        raw_signal,
        final_signal,
        sample_rate=sample_rate,
    )


def align_signals_by_stft_envelope(
    raw_signal: np.ndarray,
    final_signal: np.ndarray,
    *,
    sample_rate: int,
    frame_seconds: float = 0.25,
    hop_seconds: float = 0.10,
) -> dict[str, float]:
    """
    Align final_signal inside raw_signal using a local STFT magnitude envelope.
    """

    if sample_rate <= 0:
        raise ValueError("sample_rate must be greater than zero")
    if raw_signal.size == 0 or final_signal.size == 0:
        raise ValueError("raw_signal and final_signal must not be empty")
    if final_signal.size > raw_signal.size:
        raise ValueError("final audio is longer than raw audio")

    raw_env = compute_stft_energy_envelope(
        raw_signal,
        sample_rate=sample_rate,
        frame_seconds=frame_seconds,
        hop_seconds=hop_seconds,
    )
    final_env = compute_stft_energy_envelope(
        final_signal,
        sample_rate=sample_rate,
        frame_seconds=frame_seconds,
        hop_seconds=hop_seconds,
    )

    if final_env.size > raw_env.size:
        raise ValueError("final envelope is longer than raw envelope")

    offset_frames, confidence = normalized_sliding_correlation(raw_env, final_env)
    raw_start_s = offset_frames * hop_seconds

    return {
        "raw_start_s": round(float(raw_start_s), 3),
        "alignment_confidence": round(float(confidence), 6),
    }


def compute_stft_energy_envelope(
    signal: np.ndarray,
    *,
    sample_rate: int,
    frame_seconds: float,
    hop_seconds: float,
) -> np.ndarray:
    """
    Build a deterministic STFT-style RMS energy envelope.

    This avoids cloud APIs and external fingerprint tools.
    """

    frame_size = max(1, int(round(sample_rate * frame_seconds)))
    hop_size = max(1, int(round(sample_rate * hop_seconds)))

    mono = np.asarray(signal, dtype=np.float32)
    if mono.size < frame_size:
        mono = np.pad(mono, (0, frame_size - mono.size))

    window = np.hanning(frame_size).astype(np.float32)
    values: list[float] = []

    for start in range(0, mono.size - frame_size + 1, hop_size):
        frame = mono[start : start + frame_size] * window
        spectrum = np.fft.rfft(frame)
        magnitude = np.abs(spectrum)
        energy = float(np.sqrt(np.mean(np.square(magnitude))))
        values.append(energy)

    if not values:
        return np.array([0.0], dtype=np.float32)

    envelope = np.array(values, dtype=np.float32)
    return normalize_vector(envelope)


def normalized_sliding_correlation(
    raw_values: np.ndarray,
    final_values: np.ndarray,
) -> tuple[int, float]:
    """Return best offset and normalized correlation confidence."""

    raw = normalize_vector(np.asarray(raw_values, dtype=np.float32))
    target = normalize_vector(np.asarray(final_values, dtype=np.float32))

    if target.size > raw.size:
        raise ValueError("target cannot be longer than raw")

    target_norm = float(np.linalg.norm(target))
    if target_norm <= 0:
        return 0, 0.0

    best_offset = 0
    best_score = -1.0

    for offset in range(0, raw.size - target.size + 1):
        window = raw[offset : offset + target.size]
        window_norm = float(np.linalg.norm(window))
        if window_norm <= 0:
            score = 0.0
        else:
            score = float(np.dot(window, target) / (window_norm * target_norm))

        if score > best_score:
            best_score = score
            best_offset = offset

    confidence = max(0.0, min(1.0, best_score))
    return best_offset, confidence


def build_cut_segments_from_kept(
    *,
    raw_duration_seconds: float,
    kept_segments: list[dict[str, Any]],
    raw_audio_path: str | Path | None = None,
    ffmpeg_path: str | None = None,
) -> list[dict[str, Any]]:
    """Invert kept segments into cut segments over the raw timeline."""

    normalized_kept = normalize_segments(kept_segments, raw_duration_seconds=raw_duration_seconds)
    cuts: list[CutSegment] = []
    cursor = 0.0

    for segment in normalized_kept:
        start = float(segment["raw_start_s"])
        end = float(segment["raw_end_s"])

        if start > cursor:
            cuts.append(
                CutSegment(
                    raw_start_s=round(cursor, 3),
                    raw_end_s=round(start, 3),
                    cut_reason_class=classify_cut_reason(
                        raw_audio_path,
                        start_s=cursor,
                        end_s=start,
                        ffmpeg_path=ffmpeg_path,
                    ),
                )
            )

        cursor = max(cursor, end)

    if cursor < raw_duration_seconds:
        cuts.append(
            CutSegment(
                raw_start_s=round(cursor, 3),
                raw_end_s=round(raw_duration_seconds, 3),
                cut_reason_class=classify_cut_reason(
                    raw_audio_path,
                    start_s=cursor,
                    end_s=raw_duration_seconds,
                    ffmpeg_path=ffmpeg_path,
                ),
            )
        )

    return [segment.to_dict() for segment in cuts if segment.raw_end_s > segment.raw_start_s]


def normalize_segments(
    segments: list[dict[str, Any]],
    *,
    raw_duration_seconds: float,
) -> list[dict[str, float]]:
    """Sort, clamp and merge overlapping raw segments."""

    clean: list[dict[str, float]] = []
    for segment in segments or []:
        start = clamp_seconds(segment.get("raw_start_s", 0.0), minimum=0.0, maximum=raw_duration_seconds)
        end = clamp_seconds(segment.get("raw_end_s", 0.0), minimum=0.0, maximum=raw_duration_seconds)
        if end > start:
            clean.append({"raw_start_s": round(start, 3), "raw_end_s": round(end, 3)})

    clean.sort(key=lambda item: item["raw_start_s"])

    merged: list[dict[str, float]] = []
    for segment in clean:
        if not merged or segment["raw_start_s"] > merged[-1]["raw_end_s"]:
            merged.append(dict(segment))
        else:
            merged[-1]["raw_end_s"] = max(merged[-1]["raw_end_s"], segment["raw_end_s"])

    return merged


def classify_cut_reason(
    raw_audio_path: str | Path | None,
    *,
    start_s: float,
    end_s: float,
    ffmpeg_path: str | None = None,
    dead_air_rms_threshold: float = 0.015,
) -> str:
    """
    Conservative cut reason heuristic.

    Without audio path or readable segment, returns unknown.
    """

    if raw_audio_path is None:
        return "unknown"

    duration = max(0.0, float(end_s) - float(start_s))
    if duration <= 0:
        return "unknown"

    try:
        with tempfile.TemporaryDirectory(prefix="zenith_p5_2_cut_") as temp_dir:
            temp_wav = Path(temp_dir) / "cut.wav"
            extract_audio_to_wav(
                raw_audio_path,
                temp_wav,
                start_s=start_s,
                duration_s=duration,
                ffmpeg_path=ffmpeg_path,
            )
            samples, _ = read_wav_mono(temp_wav)
            rms = float(np.sqrt(np.mean(np.square(samples)))) if samples.size else 0.0
    except Exception:
        return "unknown"

    if rms < dead_air_rms_threshold:
        return "dead_air"
    return "low_action"


def probe_audio_sample_rate(
    media_path: str | Path,
    *,
    ffprobe_path: str | None = None,
) -> int:
    """Read first audio stream sample rate via ffprobe."""

    command = [
        ffprobe_path or get_ffprobe_path(),
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=sample_rate",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]

    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    try:
        value = int(completed.stdout.strip())
    except ValueError as exc:
        raise ValueError(f"Could not read sample rate for {media_path}") from exc

    if value <= 0:
        raise ValueError(f"Invalid sample rate for {media_path}: {value}")

    return value


def probe_media_duration_seconds(
    media_path: str | Path,
    *,
    ffprobe_path: str | None = None,
) -> float:
    """Read media duration via ffprobe."""

    command = [
        ffprobe_path or get_ffprobe_path(),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]

    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    try:
        return max(0.0, float(completed.stdout.strip()))
    except ValueError as exc:
        raise ValueError(f"Could not read duration for {media_path}") from exc


def extract_audio_to_wav(
    media_path: str | Path,
    output_wav_path: str | Path,
    *,
    sample_rate: int | None = None,
    start_s: float | None = None,
    duration_s: float | None = None,
    ffmpeg_path: str | None = None,
) -> Path:
    """Extract mono PCM WAV with local FFmpeg."""

    output_path = Path(output_wav_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [ffmpeg_path or get_ffmpeg_path(), "-y"]

    if start_s is not None:
        command.extend(["-ss", f"{max(0.0, float(start_s)):.3f}"])

    command.extend(["-i", str(media_path), "-vn", "-ac", "1"])

    if sample_rate is not None:
        command.extend(["-ar", str(int(sample_rate))])

    if duration_s is not None:
        command.extend(["-t", f"{max(0.0, float(duration_s)):.3f}"])

    command.extend(["-c:a", "pcm_s16le", str(output_path)])

    subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    return output_path


def read_wav_mono(path: str | Path) -> tuple[np.ndarray, int]:
    """Read PCM WAV as mono float32 in [-1, 1]."""

    wav_path = Path(path)
    with wave.open(str(wav_path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.getnframes()
        data = wav.readframes(frames)

    if sample_width != 2:
        raise ValueError(f"Only 16-bit PCM WAV is supported: {wav_path}")

    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)

    return samples, sample_rate


def normalize_vector(values: np.ndarray) -> np.ndarray:
    """Zero-mean/unit-variance vector normalization."""

    array = np.asarray(values, dtype=np.float32)
    if array.size == 0:
        return array

    mean = float(np.mean(array))
    std = float(np.std(array))

    if not math.isfinite(std) or std <= 1e-8:
        return np.zeros_like(array, dtype=np.float32)

    return ((array - mean) / std).astype(np.float32)


def clamp_seconds(value: Any, *, minimum: float, maximum: float) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        converted = minimum

    return max(minimum, min(maximum, converted))
