from __future__ import annotations

import math
import subprocess
import tempfile
import wave
from dataclasses import dataclass, replace
from enum import IntEnum
from pathlib import Path
from typing import Any

import numpy as np


class VoiceIntensity(IntEnum):
    NORMAL = 0
    LEISE_ERHOEHT = 1
    SCHREIEN = 2
    BRUELLEN = 3

    @property
    def label(self) -> str:
        return {
            VoiceIntensity.NORMAL: "normal",
            VoiceIntensity.LEISE_ERHOEHT: "leise_erhoeht",
            VoiceIntensity.SCHREIEN: "schreien",
            VoiceIntensity.BRUELLEN: "bruellen",
        }[self]


@dataclass(frozen=True)
class VoiceIntensityPoint:
    timestamp: float
    intensity: VoiceIntensity
    lufs: float
    rms_dbfs: float
    speaker: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "intensity": int(self.intensity),
            "intensity_label": self.intensity.label,
            "lufs": self.lufs,
            "rms_dbfs": self.rms_dbfs,
            "speaker": self.speaker,
        }


class VoiceIntensityAnalyzer:
    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        sample_rate: int = 16000,
        window_seconds: float = 1.0,
        adaptive_calibration: bool = True,
    ) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.sample_rate = int(sample_rate)
        self.window_seconds = float(window_seconds)
        self.adaptive_calibration = bool(adaptive_calibration)

    def analyze(
        self,
        audio_path: str,
        speaker: str = "ali",
        audio_stream_index: int | None = None,
    ) -> list[VoiceIntensityPoint]:
        """Measure 1-second RMS windows and classify voice intensity."""

        source = Path(audio_path)
        if not source.exists():
            raise FileNotFoundError(f"Voice intensity source not found: {audio_path}")

        with tempfile.TemporaryDirectory(prefix="zenith_voice_intensity_") as temp_dir:
            wav_path = Path(temp_dir) / "voice_intensity.wav"
            self._extract_wav(
                source_path=source,
                output_path=wav_path,
                audio_stream_index=audio_stream_index,
            )
            samples, sample_rate = read_mono_wav_samples(wav_path)

        return self.analyze_samples(
            samples=samples,
            sample_rate=sample_rate,
            speaker=speaker,
        )

    def analyze_samples(
        self,
        samples: np.ndarray,
        sample_rate: int,
        speaker: str = "ali",
    ) -> list[VoiceIntensityPoint]:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than zero")

        if samples.size == 0:
            return []

        window_size = max(1, int(sample_rate * self.window_seconds))
        total_samples = int(samples.size)

        points: list[VoiceIntensityPoint] = []
        start = 0
        while start < total_samples:
            end = min(start + window_size, total_samples)
            window = samples[start:end]
            rms = calculate_rms(window)
            rms_dbfs = rms_dbfs_from_rms(rms)
            lufs = approximate_lufs_from_rms_dbfs(rms_dbfs)
            intensity = classify_voice_intensity(lufs=lufs, rms_dbfs=rms_dbfs)
            points.append(
                VoiceIntensityPoint(
                    timestamp=round(start / sample_rate, 3),
                    intensity=intensity,
                    lufs=round(lufs, 3),
                    rms_dbfs=round(rms_dbfs, 3),
                    speaker=str(speaker or "ali"),
                )
            )
            start += window_size

        if self.adaptive_calibration:
            points = apply_adaptive_calibration(points)

        return points

    def distribution(
        self,
        points: list[VoiceIntensityPoint],
    ) -> dict[str, float]:
        if not points:
            return {intensity.label: 0.0 for intensity in VoiceIntensity}

        counts = {intensity: 0 for intensity in VoiceIntensity}
        for point in points:
            counts[point.intensity] += 1

        total = float(len(points))
        return {
            intensity.label: round((counts[intensity] / total) * 100.0, 3)
            for intensity in VoiceIntensity
        }

    def _extract_wav(
        self,
        *,
        source_path: Path,
        output_path: Path,
        audio_stream_index: int | None,
    ) -> None:
        command = [
            self.ffmpeg_path,
            "-y",
            "-v",
            "error",
            "-i",
            str(source_path),
        ]
        if audio_stream_index is not None:
            command.extend(["-map", f"0:{int(audio_stream_index)}"])
        command.extend(
            [
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(self.sample_rate),
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ]
        )

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"ffmpeg audio extraction failed: {message}")


def classify_voice_intensity(lufs: float, rms_dbfs: float) -> VoiceIntensity:
    rms_level = _classify_by_rms(rms_dbfs)
    lufs_level = _classify_by_lufs(lufs)
    return VoiceIntensity(max(int(rms_level), int(lufs_level)))


def calculate_rms(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples.astype(np.float64)))))


def rms_dbfs_from_rms(rms: float) -> float:
    if rms <= 0.0:
        return -120.0
    return 20.0 * math.log10(max(rms, 1e-12))


def approximate_lufs_from_rms_dbfs(rms_dbfs: float) -> float:
    # Speech LUFS usually lands a few dB below raw RMS dBFS without K-weighting.
    return float(rms_dbfs - 5.0)


def read_mono_wav_samples(wav_path: str | Path) -> tuple[np.ndarray, int]:
    with wave.open(str(wav_path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        frame_count = handle.getnframes()
        raw = handle.readframes(frame_count)

    if sample_width != 2:
        raise RuntimeError(f"unsupported sample width: {sample_width}")

    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)

    return samples, sample_rate


def apply_adaptive_calibration(
    points: list[VoiceIntensityPoint],
) -> list[VoiceIntensityPoint]:
    if len(points) < 4:
        return points

    detected_levels = {point.intensity for point in points}
    if len(detected_levels) >= 3:
        return points

    active_values = np.asarray(
        [point.rms_dbfs for point in points if point.rms_dbfs > -60.0],
        dtype=np.float64,
    )
    if active_values.size < 4:
        return points

    dynamic_range = float(np.max(active_values) - np.min(active_values))
    if dynamic_range < 8.0:
        return points

    p60, p85, p97 = np.percentile(active_values, [60.0, 85.0, 97.0])
    calibrated: list[VoiceIntensityPoint] = []
    for point in points:
        if point.rms_dbfs < -60.0:
            intensity = VoiceIntensity.NORMAL
        elif point.rms_dbfs >= p97:
            intensity = VoiceIntensity.BRUELLEN
        elif point.rms_dbfs >= p85:
            intensity = VoiceIntensity.SCHREIEN
        elif point.rms_dbfs >= p60:
            intensity = VoiceIntensity.LEISE_ERHOEHT
        else:
            intensity = VoiceIntensity.NORMAL
        calibrated.append(replace(point, intensity=intensity))

    return calibrated


def _classify_by_rms(rms_dbfs: float) -> VoiceIntensity:
    if rms_dbfs > -8.0:
        return VoiceIntensity.BRUELLEN
    if rms_dbfs >= -15.0:
        return VoiceIntensity.SCHREIEN
    if rms_dbfs >= -20.0:
        return VoiceIntensity.LEISE_ERHOEHT
    return VoiceIntensity.NORMAL


def _classify_by_lufs(lufs: float) -> VoiceIntensity:
    if lufs > -15.0:
        return VoiceIntensity.BRUELLEN
    if lufs >= -20.0:
        return VoiceIntensity.SCHREIEN
    if lufs >= -25.0:
        return VoiceIntensity.LEISE_ERHOEHT
    return VoiceIntensity.NORMAL
