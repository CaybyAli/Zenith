from __future__ import annotations

import math
import os
import struct
import tempfile
import wave
from pathlib import Path

import pytest

from core.rms_energy_analyzer import (
    analyze_wav_rms_energy,
    build_rms_energy_timeline_from_samples,
    calculate_rms,
    dbfs_from_rms,
    normalize_values,
)
from models.rms_energy import RmsEnergyPoint, RmsEnergyTimelineResult

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_wav(path: str, samples: list[int], sample_rate: int, n_channels: int) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))


# ─── 1. RmsEnergyPoint roundtrip ──────────────────────────────────────────────

def test_rms_energy_point_roundtrip() -> None:
    pt = RmsEnergyPoint(
        start_seconds=0.0,
        end_seconds=0.01,
        center_seconds=0.005,
        rms=0.5,
        normalized_energy=0.8,
        dbfs=-6.02,
        sample_count=480,
        is_silent=False,
        metadata={"frame": 0},
    )
    restored = RmsEnergyPoint.from_dict(pt.to_dict())
    assert restored.start_seconds == 0.0
    assert restored.end_seconds == pytest.approx(0.01)
    assert restored.center_seconds == pytest.approx(0.005)
    assert restored.rms == pytest.approx(0.5)
    assert restored.normalized_energy == pytest.approx(0.8)
    assert restored.dbfs == pytest.approx(-6.02)
    assert restored.sample_count == 480
    assert restored.is_silent is False
    assert restored.metadata == {"frame": 0}


# ─── 2. RmsEnergyTimelineResult roundtrip ─────────────────────────────────────

def test_rms_energy_timeline_result_roundtrip() -> None:
    pt = RmsEnergyPoint(
        start_seconds=0.0,
        end_seconds=0.01,
        center_seconds=0.005,
        rms=0.5,
        normalized_energy=1.0,
    )
    result = RmsEnergyTimelineResult(
        status="ok",
        source_path="/fake/audio.wav",
        sample_rate=44100,
        channels=1,
        duration_seconds=1.0,
        frame_ms=10.0,
        hop_ms=5.0,
        points=[pt],
        point_count=1,
        min_rms=0.5,
        max_rms=0.5,
        avg_rms=0.5,
        min_normalized_energy=1.0,
        max_normalized_energy=1.0,
        avg_normalized_energy=1.0,
        warnings=["w1"],
        errors=[],
        metadata={"k": "v"},
    )
    restored = RmsEnergyTimelineResult.from_dict(result.to_dict())
    assert restored.status == "ok"
    assert restored.sample_rate == 44100
    assert restored.channels == 1
    assert restored.duration_seconds == pytest.approx(1.0)
    assert restored.point_count == 1
    assert len(restored.points) == 1
    assert restored.min_rms == pytest.approx(0.5)
    assert restored.warnings == ["w1"]
    assert restored.metadata == {"k": "v"}
    assert restored.source_path == "/fake/audio.wav"


# ─── 3. calculate_rms for known samples ───────────────────────────────────────

def test_calculate_rms_for_known_samples() -> None:
    # RMS of [1, -1, 1, -1] = sqrt(mean([1,1,1,1])) = 1.0
    assert calculate_rms([1.0, -1.0, 1.0, -1.0]) == pytest.approx(1.0)
    # All zeros
    assert calculate_rms([0.0, 0.0, 0.0]) == pytest.approx(0.0)
    # Empty
    assert calculate_rms([]) == pytest.approx(0.0)


# ─── 4. normalize_values basic ────────────────────────────────────────────────

def test_normalize_values_basic() -> None:
    result = normalize_values([0.0, 0.5, 1.0])
    assert result[0] == pytest.approx(0.0)
    assert result[1] == pytest.approx(0.5)
    assert result[2] == pytest.approx(1.0)

    # all same positive value → all 1.0
    result = normalize_values([0.5, 0.5, 0.5])
    assert all(v == pytest.approx(1.0) for v in result)

    # all zero → all 0.0
    result = normalize_values([0.0, 0.0])
    assert all(v == pytest.approx(0.0) for v in result)

    # empty
    assert normalize_values([]) == []


# ─── 5. dbfs_from_rms ─────────────────────────────────────────────────────────

def test_dbfs_from_rms() -> None:
    assert dbfs_from_rms(1.0) == pytest.approx(0.0, abs=1e-6)
    assert dbfs_from_rms(0.5) == pytest.approx(-6.0206, abs=0.001)
    assert dbfs_from_rms(0.0) is None
    assert dbfs_from_rms(-0.1) is None


# ─── 6. build_timeline_from_samples creates points ────────────────────────────

def test_build_timeline_from_samples_creates_points() -> None:
    sample_rate = 1000
    samples = [0.5 * ((-1) ** i) for i in range(1000)]
    result = build_rms_energy_timeline_from_samples(
        samples=samples,
        sample_rate=sample_rate,
        frame_ms=100.0,
        hop_ms=100.0,
    )
    assert result.status == "ok"
    assert result.point_count > 0
    assert result.duration_seconds == pytest.approx(1.0)
    assert len(result.points) == result.point_count
    for p in result.points:
        assert p.start_seconds >= 0.0
        assert p.end_seconds > p.start_seconds
        assert p.center_seconds == pytest.approx((p.start_seconds + p.end_seconds) / 2.0)


# ─── 7. build_timeline handles short samples (< 1 frame) ─────────────────────

def test_build_timeline_handles_short_samples() -> None:
    sample_rate = 1000
    samples = [0.1, -0.1, 0.1, 0.2, -0.2]
    result = build_rms_energy_timeline_from_samples(
        samples=samples,
        sample_rate=sample_rate,
        frame_ms=100.0,
        hop_ms=100.0,
    )
    assert result.status in ("ok", "completed_with_warnings")
    assert result.point_count == 1


# ─── 8. build_timeline normalizes energy ──────────────────────────────────────

def test_build_timeline_normalizes_energy() -> None:
    sample_rate = 1000
    # First half quiet, second half loud
    quiet = [0.01] * 500
    loud = [0.8 * ((-1) ** i) for i in range(500)]
    samples = quiet + loud
    result = build_rms_energy_timeline_from_samples(
        samples=samples,
        sample_rate=sample_rate,
        frame_ms=100.0,
        hop_ms=100.0,
    )
    assert result.max_normalized_energy == pytest.approx(1.0)
    assert result.min_normalized_energy >= 0.0
    # The last few points (loud) should have higher normalized energy than the first few (quiet)
    first_norm = result.points[0].normalized_energy
    last_norm = result.points[-1].normalized_energy
    assert last_norm > first_norm


# ─── 9. build_timeline marks silent points ────────────────────────────────────

def test_build_timeline_marks_silent_points() -> None:
    sample_rate = 1000
    samples = [0.0] * 500
    result = build_rms_energy_timeline_from_samples(
        samples=samples,
        sample_rate=sample_rate,
        frame_ms=100.0,
        hop_ms=100.0,
    )
    assert result.max_rms == pytest.approx(0.0)
    assert all(p.is_silent for p in result.points)


# ─── 10. build_timeline invalid sample_rate fails ─────────────────────────────

def test_build_timeline_invalid_sample_rate_fails() -> None:
    result = build_rms_energy_timeline_from_samples(samples=[0.5], sample_rate=0)
    assert result.status == "failed"
    assert "invalid_sample_rate" in result.errors

    result = build_rms_energy_timeline_from_samples(samples=[0.5], sample_rate=-1)
    assert result.status == "failed"
    assert "invalid_sample_rate" in result.errors


# ─── 11. analyze_wav reads mono 16-bit ────────────────────────────────────────

def test_analyze_wav_rms_energy_reads_mono_16bit() -> None:
    sample_rate = 8000
    n_frames = 4000
    samples = [int(16000 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(n_frames)]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    try:
        _write_wav(tmp_path, samples, sample_rate, n_channels=1)
        result = analyze_wav_rms_energy(tmp_path, frame_ms=10.0, hop_ms=10.0)
        assert result.status == "ok"
        assert result.sample_rate == sample_rate
        assert result.channels == 1
        assert result.point_count > 0
        assert result.duration_seconds == pytest.approx(n_frames / sample_rate, rel=0.01)
    finally:
        os.unlink(tmp_path)


# ─── 12. analyze_wav reads stereo 16-bit ──────────────────────────────────────

def test_analyze_wav_rms_energy_reads_stereo_16bit() -> None:
    sample_rate = 8000
    n_frames = 2000
    # interleaved stereo: left channel, right channel
    left = [int(16000 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(n_frames)]
    right = [int(8000 * math.sin(2 * math.pi * 880 * i / sample_rate)) for i in range(n_frames)]
    interleaved = [v for pair in zip(left, right) for v in pair]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    try:
        _write_wav(tmp_path, interleaved, sample_rate, n_channels=2)
        result = analyze_wav_rms_energy(tmp_path, frame_ms=10.0, hop_ms=10.0)
        assert result.status == "ok"
        assert result.channels == 2
        assert result.point_count > 0
    finally:
        os.unlink(tmp_path)


# ─── 13. analyze_wav missing file fails ───────────────────────────────────────

def test_analyze_wav_missing_file_fails() -> None:
    result = analyze_wav_rms_energy("/nonexistent/path/audio_zzz.wav")
    assert result.status == "failed"
    assert any("wav_file_missing" in e for e in result.errors)


# ─── 14. analyze_wav bad file fails ───────────────────────────────────────────

def test_analyze_wav_bad_file_fails() -> None:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, mode="w") as f:
        f.write("this is not a wav file at all")
        tmp_path = f.name
    try:
        result = analyze_wav_rms_energy(tmp_path)
        assert result.status == "failed"
        assert any("wav_read_failed" in e for e in result.errors)
    finally:
        os.unlink(tmp_path)


# ─── 15. BOM and newline hygiene ──────────────────────────────────────────────

def test_rms_energy_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        REPO_ROOT / "models" / "rms_energy.py",
        REPO_ROOT / "core" / "rms_energy_analyzer.py",
        REPO_ROOT / "tests" / "test_rms_energy_timeline_foundation_smoke.py",
    ]
    for path in files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
