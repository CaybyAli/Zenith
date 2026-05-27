from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest

from core.voice_intensity_analyzer import (
    VoiceIntensity,
    VoiceIntensityAnalyzer,
    classify_voice_intensity,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_001_RAW = PROJECT_ROOT / "learning_corpus" / "pairs" / "pair_001" / "raw.mp4"


def _samples_for_rms_levels(levels_dbfs: list[float], sample_rate: int = 16000) -> np.ndarray:
    chunks: list[np.ndarray] = []
    for dbfs in levels_dbfs:
        rms = 10 ** (dbfs / 20.0)
        chunks.append(np.full(sample_rate, rms, dtype=np.float32))
    return np.concatenate(chunks)


def _write_wav(path: Path, samples: np.ndarray, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1.0, 1.0)
    raw = (pcm * 32767.0).astype("<i2").tobytes()
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(raw)


def test_classify_voice_intensity_uses_four_levels() -> None:
    assert classify_voice_intensity(lufs=-30.0, rms_dbfs=-30.0) == VoiceIntensity.NORMAL
    assert classify_voice_intensity(lufs=-23.0, rms_dbfs=-18.0) == VoiceIntensity.LEISE_ERHOEHT
    assert classify_voice_intensity(lufs=-18.0, rms_dbfs=-12.0) == VoiceIntensity.SCHREIEN
    assert classify_voice_intensity(lufs=-14.0, rms_dbfs=-6.0) == VoiceIntensity.BRUELLEN


def test_analyze_samples_detects_all_four_levels() -> None:
    analyzer = VoiceIntensityAnalyzer()
    samples = _samples_for_rms_levels([-30.0, -18.0, -12.0, -6.0])

    points = analyzer.analyze_samples(samples=samples, sample_rate=16000)

    assert [point.intensity for point in points] == [
        VoiceIntensity.NORMAL,
        VoiceIntensity.LEISE_ERHOEHT,
        VoiceIntensity.SCHREIEN,
        VoiceIntensity.BRUELLEN,
    ]
    assert [point.timestamp for point in points] == [0.0, 1.0, 2.0, 3.0]


def test_distribution_reports_percentages() -> None:
    analyzer = VoiceIntensityAnalyzer()
    samples = _samples_for_rms_levels([-30.0, -18.0, -12.0, -6.0])
    points = analyzer.analyze_samples(samples=samples, sample_rate=16000)

    distribution = analyzer.distribution(points)

    assert distribution == {
        "normal": 25.0,
        "leise_erhoeht": 25.0,
        "schreien": 25.0,
        "bruellen": 25.0,
    }


def test_analyze_wav_source_via_ffmpeg(tmp_path) -> None:
    wav_path = tmp_path / "levels.wav"
    _write_wav(wav_path, _samples_for_rms_levels([-30.0, -6.0]))

    points = VoiceIntensityAnalyzer().analyze(str(wav_path))

    assert len(points) == 2
    assert points[0].intensity == VoiceIntensity.NORMAL
    assert points[1].intensity == VoiceIntensity.BRUELLEN
    assert points[0].speaker == "ali"


def test_pair_001_voice_intensity_produces_timeline() -> None:
    if not PAIR_001_RAW.exists():
        pytest.skip("pair_001 raw.mp4 not available in this checkout")

    analyzer = VoiceIntensityAnalyzer()
    points = analyzer.analyze(str(PAIR_001_RAW))
    distribution = analyzer.distribution(points)

    assert len(points) > 60
    assert set(distribution) == {"normal", "leise_erhoeht", "schreien", "bruellen"}
    assert round(sum(distribution.values()), 1) == 100.0
    assert all(distribution[key] > 0.0 for key in distribution)
    assert all(point.speaker == "ali" for point in points)
