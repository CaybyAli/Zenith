from __future__ import annotations

import struct
import wave
from pathlib import Path

from core.beat_detector import (
    analyze_wav_beats,
    build_energy_envelope,
    calculate_frame_energy,
    detect_beat_candidates,
    detect_beats_from_samples,
    estimate_bpm_from_beats,
    filter_beats_by_min_distance,
)
from models.beat_detection import BeatDetectionResult, BeatPoint


def _pulse_samples(
    sample_rate: int = 1000,
    duration_seconds: float = 2.0,
    pulse_times: list[float] | None = None,
    pulse_width_samples: int = 8,
) -> list[float]:
    pulse_times = pulse_times or [0.25, 0.75, 1.25, 1.75]
    sample_count = int(sample_rate * duration_seconds)
    samples = [0.02 for _ in range(sample_count)]

    for pulse_time in pulse_times:
        start = int(pulse_time * sample_rate)
        for offset in range(pulse_width_samples):
            index = start + offset
            if 0 <= index < len(samples):
                samples[index] = 1.0

    return samples


def _write_wav_16bit(
    path: Path,
    samples: list[float],
    sample_rate: int = 1000,
    channels: int = 1,
) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for sample in samples:
            value = int(max(-1.0, min(1.0, sample)) * 32767)
            if channels == 1:
                frames.extend(struct.pack("<h", value))
            else:
                for _ in range(channels):
                    frames.extend(struct.pack("<h", value))

        wav_file.writeframes(bytes(frames))


def test_beat_point_roundtrip() -> None:
    beat = BeatPoint(
        time_seconds=1.25,
        strength=0.9,
        confidence=0.8,
        energy=2.5,
        local_energy=1.0,
        average_energy=0.8,
        source_index=4,
        is_downbeat_candidate=True,
        bpm_context=120.0,
        reason="test_peak",
        warnings=["small_warning"],
        errors=[],
        metadata={"source": "unit"},
    )

    loaded = BeatPoint.from_dict(beat.to_dict())

    assert loaded.time_seconds == 1.25
    assert loaded.strength == 0.9
    assert loaded.confidence == 0.8
    assert loaded.source_index == 4
    assert loaded.is_downbeat_candidate is True
    assert loaded.bpm_context == 120.0
    assert loaded.metadata["source"] == "unit"


def test_beat_detection_result_roundtrip() -> None:
    result = BeatDetectionResult(
        status="ok",
        input_path="demo.wav",
        beats=[BeatPoint(time_seconds=0.5, strength=0.7)],
        beat_count=1,
        estimated_bpm=120.0,
        average_beat_interval_seconds=0.5,
        duration_seconds=2.0,
        sample_rate=1000,
        channels=1,
        energy_frame_count=12,
        metadata={"kind": "roundtrip"},
    )

    loaded = BeatDetectionResult.from_dict(result.to_dict())

    assert loaded.status == "ok"
    assert loaded.input_path == "demo.wav"
    assert loaded.beat_count == 1
    assert len(loaded.beats) == 1
    assert loaded.beats[0].time_seconds == 0.5
    assert loaded.estimated_bpm == 120.0
    assert loaded.metadata["kind"] == "roundtrip"


def test_calculate_frame_energy_basic() -> None:
    energy = calculate_frame_energy([1.0, -1.0, 0.0, 0.5])

    assert energy == 0.5625


def test_build_energy_envelope_creates_frames() -> None:
    samples = [0.1 for _ in range(200)]

    envelope = build_energy_envelope(samples, sample_rate=1000, frame_ms=50, hop_ms=25)

    assert len(envelope) > 1
    assert envelope[0]["index"] == 0
    assert envelope[0]["start_seconds"] == 0.0
    assert envelope[0]["end_seconds"] > 0.0
    assert envelope[0]["energy"] > 0.0


def test_short_samples_create_one_frame() -> None:
    samples = [0.5, 0.5]

    envelope = build_energy_envelope(samples, sample_rate=1000, frame_ms=50, hop_ms=25)

    assert len(envelope) == 1
    assert envelope[0]["energy"] > 0.0


def test_detect_beat_candidates_detects_clear_peak() -> None:
    envelope = [
        {"index": 0, "center_seconds": 0.00, "energy": 1.0},
        {"index": 1, "center_seconds": 0.25, "energy": 1.1},
        {"index": 2, "center_seconds": 0.50, "energy": 5.0},
        {"index": 3, "center_seconds": 0.75, "energy": 1.0},
        {"index": 4, "center_seconds": 1.00, "energy": 0.9},
    ]

    beats = detect_beat_candidates(envelope, peak_threshold=1.35, local_window=2)

    assert len(beats) == 1
    assert beats[0].time_seconds == 0.5
    assert beats[0].strength > 0.0
    assert beats[0].confidence > 0.0
    assert beats[0].reason == "local_energy_peak"


def test_flat_energy_detects_no_beats() -> None:
    envelope = [
        {"index": index, "center_seconds": index * 0.25, "energy": 1.0}
        for index in range(8)
    ]

    beats = detect_beat_candidates(envelope, peak_threshold=1.35, local_window=2)

    assert beats == []


def test_filter_beats_by_min_distance_keeps_strongest() -> None:
    beats = [
        BeatPoint(time_seconds=0.10, strength=0.2, confidence=0.2, energy=2.0),
        BeatPoint(time_seconds=0.20, strength=0.9, confidence=0.8, energy=5.0),
        BeatPoint(time_seconds=0.70, strength=0.4, confidence=0.4, energy=3.0),
    ]

    filtered = filter_beats_by_min_distance(beats, min_beat_distance_seconds=0.25)

    assert len(filtered) == 2
    assert filtered[0].time_seconds == 0.20
    assert filtered[1].time_seconds == 0.70


def test_estimate_bpm_from_regular_beats() -> None:
    beats = [
        BeatPoint(time_seconds=0.0),
        BeatPoint(time_seconds=0.5),
        BeatPoint(time_seconds=1.0),
        BeatPoint(time_seconds=1.5),
    ]

    bpm = estimate_bpm_from_beats(beats)

    assert bpm == 120.0


def test_estimate_bpm_returns_none_for_too_few_beats() -> None:
    bpm = estimate_bpm_from_beats([BeatPoint(time_seconds=0.0)])

    assert bpm is None


def test_detect_beats_from_samples_detects_pulses() -> None:
    samples = _pulse_samples()

    result = detect_beats_from_samples(
        samples=samples,
        sample_rate=1000,
        channels=1,
        frame_ms=50,
        hop_ms=25,
        peak_threshold=1.35,
        min_beat_distance_seconds=0.25,
    )

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.beat_count >= 3
    assert result.estimated_bpm is not None
    assert 40.0 <= result.estimated_bpm <= 240.0
    assert result.energy_frame_count > 0


def test_detect_beats_from_samples_empty_safe() -> None:
    result = detect_beats_from_samples([], sample_rate=1000)

    assert result.status == "completed_with_warnings"
    assert result.beat_count == 0
    assert "empty_samples" in result.warnings


def test_detect_beats_from_samples_silent_safe() -> None:
    result = detect_beats_from_samples([0.0 for _ in range(1000)], sample_rate=1000)

    assert result.status == "completed_with_warnings"
    assert result.beat_count == 0
    assert "no_beats_detected" in result.warnings


def test_analyze_wav_beats_mono_16bit(tmp_path: Path) -> None:
    wav_path = tmp_path / "mono.wav"
    samples = _pulse_samples()
    _write_wav_16bit(wav_path, samples, sample_rate=1000, channels=1)

    result = analyze_wav_beats(wav_path)

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.input_path == str(wav_path)
    assert result.sample_rate == 1000
    assert result.channels == 1
    assert result.beat_count >= 3


def test_analyze_wav_beats_stereo_16bit(tmp_path: Path) -> None:
    wav_path = tmp_path / "stereo.wav"
    samples = _pulse_samples()
    _write_wav_16bit(wav_path, samples, sample_rate=1000, channels=2)

    result = analyze_wav_beats(wav_path)

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.input_path == str(wav_path)
    assert result.sample_rate == 1000
    assert result.channels == 2
    assert result.beat_count >= 3


def test_analyze_wav_missing_file_failed(tmp_path: Path) -> None:
    wav_path = tmp_path / "missing.wav"

    result = analyze_wav_beats(wav_path)

    assert result.status == "failed"
    assert "wav_file_missing" in result.errors


def test_analyze_wav_bad_file_failed(tmp_path: Path) -> None:
    wav_path = tmp_path / "bad.wav"
    wav_path.write_text("not a real wav", encoding="utf-8")

    result = analyze_wav_beats(wav_path)

    assert result.status == "failed"
    assert "wav_read_failed" in result.errors


def test_beat_detector_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/beat_detection.py"),
        Path("core/beat_detector.py"),
        Path("tests/test_beat_detection_foundation_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
