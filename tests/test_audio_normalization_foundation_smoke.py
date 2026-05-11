from __future__ import annotations

import math
import pathlib
import struct
import tempfile
import wave

import pytest

from models.audio_normalization import AudioLevelStats, AudioNormalizationResult
from core.audio_normalization_analyzer import (
    analyze_audio_samples,
    analyze_wav_audio_normalization,
    build_normalization_result_from_stats,
    calculate_rms,
    clamp_gain_to_peak_headroom,
    dbfs_from_amplitude,
)


def _write_wav(path: str, n_channels: int, sample_rate: int, samples: list[float]) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw = struct.pack(f"<{len(samples)}h", *[int(s * 32767) for s in samples])
        wf.writeframes(raw)


def test_audio_level_stats_roundtrip() -> None:
    stats = AudioLevelStats(
        peak_amplitude=0.8,
        rms=0.4,
        peak_dbfs=-1.94,
        rms_dbfs=-7.96,
        headroom_db=1.94,
        dynamic_range_db=6.02,
        clipping_sample_count=0,
        clipping_ratio=0.0,
        sample_count=100,
        duration_seconds=0.5,
        sample_rate=44100,
        channels=2,
        warnings=["test_warn"],
        errors=[],
        metadata={"key": "val"},
    )
    d = stats.to_dict()
    restored = AudioLevelStats.from_dict(d)
    assert restored.peak_amplitude == stats.peak_amplitude
    assert restored.rms == stats.rms
    assert restored.peak_dbfs == stats.peak_dbfs
    assert restored.rms_dbfs == stats.rms_dbfs
    assert restored.headroom_db == stats.headroom_db
    assert restored.dynamic_range_db == stats.dynamic_range_db
    assert restored.clipping_sample_count == stats.clipping_sample_count
    assert restored.sample_count == stats.sample_count
    assert restored.sample_rate == stats.sample_rate
    assert restored.channels == stats.channels
    assert restored.warnings == stats.warnings
    assert restored.metadata == stats.metadata


def test_audio_normalization_result_roundtrip() -> None:
    stats = AudioLevelStats(sample_count=50, rms=0.1, rms_dbfs=-20.0, peak_dbfs=-3.0)
    result = AudioNormalizationResult(
        status="ok",
        input_path="/tmp/test.wav",
        level_status="normal",
        stats=stats,
        target_rms_dbfs=-18.0,
        target_peak_dbfs=-1.0,
        recommended_gain_db=2.0,
        limited_gain_db=2.0,
        gain_limited_by_peak=False,
        would_clip_after_gain=False,
        normalization_needed=True,
        recommendation="apply_gain",
        warnings=["w1"],
        errors=[],
        metadata={"run": 1},
    )
    d = result.to_dict()
    restored = AudioNormalizationResult.from_dict(d)
    assert restored.status == result.status
    assert restored.input_path == result.input_path
    assert restored.level_status == result.level_status
    assert restored.recommended_gain_db == result.recommended_gain_db
    assert restored.limited_gain_db == result.limited_gain_db
    assert restored.gain_limited_by_peak == result.gain_limited_by_peak
    assert restored.normalization_needed == result.normalization_needed
    assert restored.recommendation == result.recommendation
    assert restored.warnings == result.warnings
    assert restored.stats.sample_count == stats.sample_count
    assert restored.stats.rms_dbfs == stats.rms_dbfs


def test_calculate_rms_basic_values() -> None:
    assert calculate_rms([1, -1, 1, -1]) == pytest.approx(1.0)
    assert calculate_rms([0, 0, 0]) == pytest.approx(0.0)
    assert calculate_rms([0.5, -0.5]) == pytest.approx(0.5)


def test_calculate_rms_empty() -> None:
    assert calculate_rms([]) == 0.0


def test_dbfs_from_amplitude() -> None:
    assert dbfs_from_amplitude(1.0) == pytest.approx(0.0)
    assert dbfs_from_amplitude(0.5) == pytest.approx(-6.0206, abs=0.001)
    assert dbfs_from_amplitude(0.0) is None
    assert dbfs_from_amplitude(-1.0) is None


def test_clamp_gain_to_peak_headroom() -> None:
    # recommended +10, peak -3, target -1 → max allowed +2, limited True
    gain, limited = clamp_gain_to_peak_headroom(10.0, -3.0, -1.0)
    assert gain == pytest.approx(2.0)
    assert limited is True

    # recommended +1, peak -10, target -1 → max allowed +9, not limited
    gain, limited = clamp_gain_to_peak_headroom(1.0, -10.0, -1.0)
    assert gain == pytest.approx(1.0)
    assert limited is False

    # peak None → unchanged, not limited
    gain, limited = clamp_gain_to_peak_headroom(5.0, None, -1.0)
    assert gain == pytest.approx(5.0)
    assert limited is False


def test_analyze_audio_samples_normal_audio() -> None:
    samples = [0.1, -0.1, 0.2, -0.2]
    stats = analyze_audio_samples(samples)
    assert stats.sample_count == 4
    assert stats.peak_amplitude == pytest.approx(0.2)
    assert stats.rms > 0.0
    assert stats.peak_dbfs is not None
    assert stats.peak_dbfs < 0.0
    assert stats.clipping_sample_count == 0
    assert "no_samples" not in stats.warnings
    assert "clipping_detected" not in stats.warnings


def test_analyze_audio_samples_silent_audio() -> None:
    samples = [0.0, 0.0, 0.0]
    stats = analyze_audio_samples(samples)
    assert stats.rms == pytest.approx(0.0)
    assert stats.peak_dbfs is None
    assert stats.rms_dbfs is None
    assert stats.sample_count == 3


def test_analyze_audio_samples_clipping_detected() -> None:
    samples = [1.0, -1.0, 0.5]
    stats = analyze_audio_samples(samples, clipping_threshold=0.999)
    assert stats.clipping_sample_count >= 2
    assert "clipping_detected" in stats.warnings


def test_analyze_audio_samples_out_of_range_warning() -> None:
    samples = [2.0, -2.0, 0.1]
    stats = analyze_audio_samples(samples)
    assert "samples_out_of_range" in stats.warnings
    assert stats.peak_amplitude <= 1.0


def test_build_normalization_result_too_quiet() -> None:
    stats = AudioLevelStats(
        sample_count=100,
        rms=0.056,
        rms_dbfs=-25.0,
        peak_amplitude=0.316,
        peak_dbfs=-10.0,
        clipping_sample_count=0,
    )
    result = build_normalization_result_from_stats(stats)
    assert result.level_status == "too_quiet"
    assert result.normalization_needed is True
    assert result.recommendation == "apply_gain"
    assert result.recommended_gain_db > 0.0


def test_build_normalization_result_too_loud() -> None:
    stats = AudioLevelStats(
        sample_count=100,
        rms=0.562,
        rms_dbfs=-5.0,
        peak_amplitude=0.891,
        peak_dbfs=-1.0,
        clipping_sample_count=0,
    )
    result = build_normalization_result_from_stats(stats)
    assert result.level_status in ("too_loud", "clipped")
    assert result.normalization_needed is True
    assert result.recommended_gain_db < 0.0 or result.recommendation in ("reduce_gain", "fix_clipping")


def test_build_normalization_result_normal_audio() -> None:
    # rms_dbfs ≈ -18, peak_dbfs -3 → normal, near target
    stats = AudioLevelStats(
        sample_count=100,
        rms=0.126,
        rms_dbfs=-18.0,
        peak_amplitude=0.708,
        peak_dbfs=-3.0,
        clipping_sample_count=0,
    )
    result = build_normalization_result_from_stats(stats)
    assert result.level_status == "normal"
    assert result.recommendation in ("no_normalization_needed", "apply_gain", "reduce_gain")


def test_build_normalization_result_gain_limited_by_peak() -> None:
    # rms_dbfs -30, peak_dbfs -3; target_rms -18, target_peak -1
    # recommended = -18 - (-30) = +12; max_allowed = -1 - (-3) = +2 → limited to +2
    stats = AudioLevelStats(
        sample_count=100,
        rms=0.031,
        rms_dbfs=-30.0,
        peak_amplitude=0.708,
        peak_dbfs=-3.0,
        clipping_sample_count=0,
    )
    result = build_normalization_result_from_stats(
        stats, target_rms_dbfs=-18.0, target_peak_dbfs=-1.0
    )
    assert result.gain_limited_by_peak is True
    assert result.limited_gain_db == pytest.approx(2.0)


def test_build_normalization_result_silent() -> None:
    stats = AudioLevelStats(
        sample_count=100,
        rms=0.0,
        peak_amplitude=0.0,
    )
    result = build_normalization_result_from_stats(stats)
    assert result.level_status == "silent"
    assert result.recommendation == "audio_silent"


def test_analyze_wav_audio_normalization_mono_16bit() -> None:
    samples = [0.1, -0.1, 0.2, -0.2, 0.15, -0.15, 0.05, -0.05]
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    try:
        _write_wav(tmp_path, n_channels=1, sample_rate=8000, samples=samples)
        result = analyze_wav_audio_normalization(tmp_path)
        assert result.status in ("ok", "completed_with_warnings")
        assert result.stats.sample_rate == 8000
        assert result.stats.channels == 1
        assert result.stats.sample_count > 0
    finally:
        pathlib.Path(tmp_path).unlink(missing_ok=True)


def test_analyze_wav_audio_normalization_stereo_16bit() -> None:
    # interleaved stereo: L,R,L,R,...
    samples = [0.1, -0.1, 0.2, -0.2, 0.3, -0.3, 0.05, -0.05]
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    try:
        _write_wav(tmp_path, n_channels=2, sample_rate=8000, samples=samples)
        result = analyze_wav_audio_normalization(tmp_path)
        assert result.stats.channels == 2
        assert result.stats.sample_count > 0
    finally:
        pathlib.Path(tmp_path).unlink(missing_ok=True)


def test_analyze_wav_missing_file_failed() -> None:
    result = analyze_wav_audio_normalization("/nonexistent/path/audio.wav")
    assert result.status == "failed"
    assert "wav_file_missing" in result.errors


def test_analyze_wav_bad_file_failed() -> None:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, mode="w") as f:
        f.write("this is not a wav file")
        tmp_path = f.name
    try:
        result = analyze_wav_audio_normalization(tmp_path)
        assert result.status == "failed"
        assert any("wav_read_failed" in e for e in result.errors)
    finally:
        pathlib.Path(tmp_path).unlink(missing_ok=True)


def test_audio_normalization_files_have_no_bom_and_end_with_newline() -> None:
    root = pathlib.Path(__file__).parent.parent
    files = [
        root / "models" / "audio_normalization.py",
        root / "core" / "audio_normalization_analyzer.py",
        root / "tests" / "test_audio_normalization_foundation_smoke.py",
    ]
    for fpath in files:
        raw = fpath.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {fpath.name}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {fpath.name}"
