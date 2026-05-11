from __future__ import annotations

import json
import struct
import wave
from pathlib import Path
from types import SimpleNamespace

import core.beat_detection_runner as runner_module
from core.beat_detection_runner import (
    build_beat_detection_run_report,
    run_beat_detection_for_job,
)
from core.beat_detection_source_selector import select_beat_detection_source
from models.beat_detection import BeatDetectionResult, BeatPoint
from models.beat_detection_run import BeatDetectionRunReport
from models.beat_detection_source import BeatDetectionSourceSelection


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


def _flat_samples(
    sample_rate: int = 1000,
    duration_seconds: float = 2.0,
) -> list[float]:
    return [0.1 for _ in range(int(sample_rate * duration_seconds))]


def _write_wav_16bit(
    path: Path,
    samples: list[float],
    sample_rate: int = 1000,
    channels: int = 1,
) -> Path:
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

    return path


def _touch(path: Path) -> Path:
    path.write_bytes(b"tiny")
    return path


def test_beat_detection_run_report_roundtrip() -> None:
    report = BeatDetectionRunReport(
        status="ok",
        source_selection={"status": "selected"},
        selected_path="music.wav",
        selected_type="music_reference_audio",
        beat_detection_result={"status": "ok"},
        beats=[{"time_seconds": 0.5, "strength": 0.8}],
        beat_count=1,
        estimated_bpm=120.0,
        average_beat_interval_seconds=0.5,
        duration_seconds=2.0,
        sample_rate=1000,
        channels=1,
        energy_frame_count=12,
        max_beat_strength=0.8,
        avg_beat_strength=0.8,
        top_beat={"time_seconds": 0.5, "strength": 0.8},
        recommendation="use_beat_timeline",
        warnings=["demo_warning"],
        errors=[],
        metadata={"kind": "roundtrip"},
    )

    loaded = BeatDetectionRunReport.from_dict(report.to_dict())

    assert loaded.status == "ok"
    assert loaded.selected_path == "music.wav"
    assert loaded.selected_type == "music_reference_audio"
    assert loaded.beat_count == 1
    assert loaded.estimated_bpm == 120.0
    assert loaded.top_beat["strength"] == 0.8
    assert loaded.recommendation == "use_beat_timeline"
    assert loaded.metadata["kind"] == "roundtrip"


def test_runner_analyzes_existing_music_reference_audio_wav(tmp_path: Path) -> None:
    music_wav = _write_wav_16bit(tmp_path / "music.wav", _pulse_samples())
    manifest = {"music_reference_audio_path": str(music_wav)}

    report = build_beat_detection_run_report(preprocessing_manifest=manifest)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_type == "music_reference_audio"
    assert report.selected_path == str(music_wav)
    assert report.beat_count >= 3
    assert report.recommendation == "use_beat_timeline"


def test_runner_analyzes_analysis_audio_fallback_wav(tmp_path: Path) -> None:
    analysis_wav = _write_wav_16bit(tmp_path / "analysis.wav", _pulse_samples())
    manifest = {"analysis_audio_path": str(analysis_wav)}

    report = build_beat_detection_run_report(preprocessing_manifest=manifest)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_type == "analysis_audio"
    assert report.selected_path == str(analysis_wav)
    assert report.beat_count >= 3


def test_runner_blocks_missing_music_reference_audio(tmp_path: Path) -> None:
    missing_music = tmp_path / "missing_music.wav"
    analysis_wav = _write_wav_16bit(tmp_path / "analysis.wav", _pulse_samples())
    manifest = {
        "music_reference_audio_path": str(missing_music),
        "analysis_audio_path": str(analysis_wav),
    }

    report = build_beat_detection_run_report(preprocessing_manifest=manifest)

    assert report.status == "blocked_missing_preprocessed_audio"
    assert report.selected_type == "planned_music_reference_audio"
    assert report.selected_path == str(missing_music)
    assert report.beat_count == 0
    assert report.recommendation == "generate_preprocessed_audio"


def test_runner_skips_original_mp4(tmp_path: Path) -> None:
    original_mp4 = _touch(tmp_path / "clip.mp4")

    report = build_beat_detection_run_report(original_source_path=str(original_mp4))

    assert report.status == "skipped_unsupported_source"
    assert report.selected_type == "unsupported_original_source"
    assert report.selected_path == str(original_mp4)
    assert report.recommendation == "extract_audio_first"


def test_runner_original_wav_fallback(tmp_path: Path) -> None:
    original_wav = _write_wav_16bit(tmp_path / "original.wav", _pulse_samples())

    report = build_beat_detection_run_report(original_source_path=str(original_wav))

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_type == "original_wav"
    assert report.selected_path == str(original_wav)
    assert report.beat_count >= 3


def test_runner_no_audio_source_safe() -> None:
    report = build_beat_detection_run_report()

    assert report.status == "skipped_no_audio_source"
    assert report.selected_type == "none"
    assert report.recommendation == "no_audio_source_available"
    assert "no_beat_detection_source_available" in report.errors


def test_runner_bad_wav_failed(tmp_path: Path) -> None:
    bad_wav = tmp_path / "bad.wav"
    bad_wav.write_text("not a real wav", encoding="utf-8")
    manifest = {"music_reference_audio_path": str(bad_wav)}

    report = build_beat_detection_run_report(preprocessing_manifest=manifest)

    assert report.status == "failed"
    assert report.selected_type == "music_reference_audio"
    assert report.recommendation == "retry_or_fix_audio"
    assert "wav_read_failed" in report.errors


def test_runner_detects_beats_from_pulse_wav(tmp_path: Path) -> None:
    music_wav = _write_wav_16bit(tmp_path / "pulse.wav", _pulse_samples())
    manifest = {"music_reference_audio_path": str(music_wav)}

    report = build_beat_detection_run_report(preprocessing_manifest=manifest)

    assert report.beat_count >= 3
    assert report.estimated_bpm is not None
    assert report.max_beat_strength > 0.0
    assert report.avg_beat_strength > 0.0
    assert report.top_beat


def test_runner_no_beats_flat_wav_safe(tmp_path: Path) -> None:
    flat_wav = _write_wav_16bit(tmp_path / "flat.wav", _flat_samples())
    manifest = {"music_reference_audio_path": str(flat_wav)}

    report = build_beat_detection_run_report(preprocessing_manifest=manifest)

    assert report.status == "completed_with_warnings"
    assert report.beat_count == 0
    assert report.recommendation == "no_beats_detected"
    assert "no_beats_detected" in report.warnings


def test_run_for_job_reads_preprocessing_manifest_dict(tmp_path: Path) -> None:
    music_wav = _write_wav_16bit(tmp_path / "music.wav", _pulse_samples())
    job = SimpleNamespace(
        preprocessing_manifest={
            "music_reference_audio_path": str(music_wav),
        }
    )

    report = run_beat_detection_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_type == "music_reference_audio"
    assert report.selected_path == str(music_wav)
    assert report.beat_count >= 3


def test_run_for_job_reads_manifest_path_json(tmp_path: Path) -> None:
    music_wav = _write_wav_16bit(tmp_path / "music.wav", _pulse_samples())
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"music_reference_audio_path": str(music_wav)}),
        encoding="utf-8",
    )
    job = SimpleNamespace(preprocessing_manifest_path=str(manifest_path))

    report = run_beat_detection_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_type == "music_reference_audio"
    assert report.selected_path == str(music_wav)
    assert report.source_selection["preprocessing_manifest_path"] == str(manifest_path)


def test_run_for_job_original_wav_fallback(tmp_path: Path) -> None:
    original_wav = _write_wav_16bit(tmp_path / "original.wav", _pulse_samples())
    job = SimpleNamespace(raw_video_path=str(original_wav))

    report = run_beat_detection_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_type == "original_wav"
    assert report.selected_path == str(original_wav)
    assert report.beat_count >= 3


def test_run_for_empty_job_safe() -> None:
    job = SimpleNamespace()

    report = run_beat_detection_for_job(job)

    assert report.status == "skipped_no_audio_source"
    assert report.selected_type == "none"
    assert report.recommendation == "no_audio_source_available"


def test_runner_uses_provided_source_selection(tmp_path: Path) -> None:
    music_wav = _write_wav_16bit(tmp_path / "music.wav", _pulse_samples())
    source_selection = BeatDetectionSourceSelection(
        status="selected",
        selected_path=str(music_wav),
        selected_type="music_reference_audio",
        source_priority=["music_reference_audio", "analysis_audio", "original_wav"],
        checked_sources=[
            {
                "type": "music_reference_audio",
                "path": str(music_wav),
                "exists": True,
                "is_wav": True,
                "usable": True,
                "reason": "selected_wav_source",
            }
        ],
        recommendation="analyze_selected_wav",
    )

    report = build_beat_detection_run_report(source_selection=source_selection)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_type == "music_reference_audio"
    assert report.selected_path == str(music_wav)
    assert report.beat_count >= 3


def test_mp4_does_not_call_analyze_wav_beats(tmp_path: Path, monkeypatch) -> None:
    original_mp4 = _touch(tmp_path / "clip.mp4")
    calls = {"count": 0}

    def fake_analyze_wav_beats(*args, **kwargs):
        calls["count"] += 1
        return BeatDetectionResult(status="ok")

    monkeypatch.setattr(runner_module, "analyze_wav_beats", fake_analyze_wav_beats)

    report = build_beat_detection_run_report(original_source_path=str(original_mp4))

    assert report.status == "skipped_unsupported_source"
    assert calls["count"] == 0


def test_wav_calls_analyze_wav_beats(tmp_path: Path, monkeypatch) -> None:
    music_wav = _touch(tmp_path / "music.wav")
    manifest = {"music_reference_audio_path": str(music_wav)}
    calls = {"count": 0}

    def fake_analyze_wav_beats(*args, **kwargs):
        calls["count"] += 1
        return BeatDetectionResult(
            status="ok",
            beats=[
                BeatPoint(
                    time_seconds=0.5,
                    strength=0.8,
                    confidence=0.7,
                    energy=2.0,
                )
            ],
            beat_count=1,
            estimated_bpm=None,
            duration_seconds=1.0,
            sample_rate=1000,
            channels=1,
            energy_frame_count=10,
        )

    monkeypatch.setattr(runner_module, "analyze_wav_beats", fake_analyze_wav_beats)

    report = build_beat_detection_run_report(preprocessing_manifest=manifest)

    assert calls["count"] == 1
    assert report.status == "ok"
    assert report.beat_count == 1
    assert report.recommendation == "use_beat_timeline"


def test_beat_detection_runner_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/beat_detection_run.py"),
        Path("core/beat_detection_runner.py"),
        Path("tests/test_beat_detection_runner_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
