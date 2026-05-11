from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from models.silence_detection import SilenceDetectionResult, SilenceSegment
from models.silence_detection_run import SilenceDetectionRunReport
import core.silence_detection_runner as runner_module
from core.silence_detection_runner import (
    build_silence_detection_run_report,
    run_silence_detection_for_job,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ok_detection(
    source_path: str,
    threshold_db: float,
    min_duration_seconds: float,
    segments: list[SilenceSegment] | None = None,
) -> SilenceDetectionResult:
    segs = segments or [
        SilenceSegment(
            start_seconds=1.0,
            end_seconds=1.5,
            duration_seconds=0.5,
            threshold_db=threshold_db,
        )
    ]
    return SilenceDetectionResult(
        source_path=source_path,
        status="ok",
        threshold_db=threshold_db,
        min_duration_seconds=min_duration_seconds,
        segments=segs,
        segment_count=len(segs),
        total_silence_seconds=sum(s.duration_seconds for s in segs),
    )


def _make_failed_detection(
    source_path: str,
    threshold_db: float,
    min_duration_seconds: float,
) -> SilenceDetectionResult:
    return SilenceDetectionResult(
        source_path=source_path,
        status="failed",
        threshold_db=threshold_db,
        min_duration_seconds=min_duration_seconds,
        errors=["ffmpeg_silencedetect_failed"],
    )


# ---------------------------------------------------------------------------
# Model round-trip
# ---------------------------------------------------------------------------

def test_silence_detection_run_report_roundtrip() -> None:
    report = SilenceDetectionRunReport(
        status="ok",
        source_path="/audio/analysis.wav",
        source_type="analysis_audio",
        threshold_db=-42.0,
        min_duration_seconds=0.35,
        require_existing_audio=True,
        audio_source_selection={"selected_path": "/audio/analysis.wav"},
        parameters={"threshold_db": -42.0},
        detection_result={"segment_count": 1},
        segment_count=1,
        total_silence_seconds=0.5,
        warnings=["w1"],
        errors=[],
        recommendation="use_result",
        metadata={"extra": "data"},
    )
    d = report.to_dict()
    restored = SilenceDetectionRunReport.from_dict(d)

    assert restored.status == "ok"
    assert restored.source_path == "/audio/analysis.wav"
    assert restored.source_type == "analysis_audio"
    assert restored.threshold_db == -42.0
    assert restored.min_duration_seconds == 0.35
    assert restored.require_existing_audio is True
    assert restored.audio_source_selection == {"selected_path": "/audio/analysis.wav"}
    assert restored.parameters == {"threshold_db": -42.0}
    assert restored.detection_result == {"segment_count": 1}
    assert restored.segment_count == 1
    assert restored.total_silence_seconds == 0.5
    assert restored.warnings == ["w1"]
    assert restored.errors == []
    assert restored.recommendation == "use_result"
    assert restored.metadata == {"extra": "data"}


# ---------------------------------------------------------------------------
# Full wiring: source + params + detector
# ---------------------------------------------------------------------------

def test_runner_selects_source_resolves_params_and_runs_detector(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    analysis = audio_dir / "analysis.wav"
    analysis.write_bytes(b"")

    manifest: dict[str, Any] = {
        "analysis_audio_path": str(analysis),
        "speech_audio_path": "",
        "music_audio_path": "",
    }

    profile: dict[str, Any] = {
        "profile_id": "gaming_main",
        "audio": {
            "silence_threshold_db": -43,
            "min_silence_duration_ms": 350,
        },
    }

    captured: dict[str, Any] = {}

    def fake_detect(source_path: str, threshold_db: float, min_duration_seconds: float, **kwargs: Any) -> SilenceDetectionResult:
        captured["source_path"] = source_path
        captured["threshold_db"] = threshold_db
        captured["min_duration_seconds"] = min_duration_seconds
        return _make_ok_detection(source_path, threshold_db, min_duration_seconds)

    monkeypatch.setattr(runner_module, "detect_silence", fake_detect)

    report = build_silence_detection_run_report(
        preprocessing_manifest=manifest,
        profile=profile,
    )

    assert report.status == "ok"
    assert report.source_type == "analysis_audio"
    assert report.source_path == str(analysis)
    assert report.threshold_db == -43.0
    assert report.min_duration_seconds == pytest.approx(0.35, abs=1e-9)
    assert report.segment_count == 1
    assert captured["source_path"] == str(analysis)
    assert captured["threshold_db"] == -43.0
    assert captured["min_duration_seconds"] == pytest.approx(0.35, abs=1e-9)


def test_runner_uses_original_source_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = tmp_path / "video.mp4"
    original.write_bytes(b"")

    manifest: dict[str, Any] = {
        "analysis_audio_path": str(tmp_path / "missing_analysis.wav"),
        "speech_audio_path": str(tmp_path / "missing_speech.wav"),
        "music_audio_path": "",
    }

    def fake_detect(source_path: str, threshold_db: float, min_duration_seconds: float, **kwargs: Any) -> SilenceDetectionResult:
        return _make_ok_detection(source_path, threshold_db, min_duration_seconds)

    monkeypatch.setattr(runner_module, "detect_silence", fake_detect)

    report = build_silence_detection_run_report(
        preprocessing_manifest=manifest,
        fallback_source_path=str(original),
    )

    assert report.status == "ok"
    assert report.source_type == "original_source"
    assert report.source_path == str(original)
    assert "original_source_used_for_silence_detection" in report.warnings


def test_runner_blocks_when_planned_audio_missing_and_require_existing_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planned = str(tmp_path / "future_analysis.wav")
    manifest: dict[str, Any] = {
        "analysis_audio_path": planned,
        "speech_audio_path": "",
        "music_audio_path": "",
    }

    detect_called = {"count": 0}

    def fake_detect(*args: Any, **kwargs: Any) -> SilenceDetectionResult:
        detect_called["count"] += 1
        return _make_ok_detection("x", -40.0, 0.4)

    monkeypatch.setattr(runner_module, "detect_silence", fake_detect)

    report = build_silence_detection_run_report(
        preprocessing_manifest=manifest,
        overrides={"require_existing_audio": False},
    )

    assert report.status == "blocked"
    assert report.recommendation == "extract_audio_first"
    assert detect_called["count"] == 0


def test_runner_returns_skipped_when_no_audio_source_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detect_called = {"count": 0}

    def fake_detect(*args: Any, **kwargs: Any) -> SilenceDetectionResult:
        detect_called["count"] += 1
        return _make_ok_detection("x", -40.0, 0.4)

    monkeypatch.setattr(runner_module, "detect_silence", fake_detect)

    report = build_silence_detection_run_report(
        preprocessing_manifest=None,
        fallback_source_path=None,
    )

    assert report.status in ("skipped_no_audio_source", "blocked")
    assert "no_silence_audio_source_available" in report.errors
    assert report.segment_count == 0
    assert report.total_silence_seconds == 0.0
    assert detect_called["count"] == 0


def test_runner_returns_failed_when_detector_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = tmp_path / "analysis.wav"
    audio.write_bytes(b"")

    manifest: dict[str, Any] = {
        "analysis_audio_path": str(audio),
        "speech_audio_path": "",
        "music_audio_path": "",
    }

    def fake_detect(source_path: str, threshold_db: float, min_duration_seconds: float, **kwargs: Any) -> SilenceDetectionResult:
        return _make_failed_detection(source_path, threshold_db, min_duration_seconds)

    monkeypatch.setattr(runner_module, "detect_silence", fake_detect)

    report = build_silence_detection_run_report(
        preprocessing_manifest=manifest,
    )

    assert report.status == "failed"
    assert "ffmpeg_silencedetect_failed" in report.errors
    assert report.recommendation == "retry_or_fix_source"


# ---------------------------------------------------------------------------
# Job-based runner
# ---------------------------------------------------------------------------

def test_run_silence_detection_for_job_reads_job_manifest_and_profile_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = tmp_path / "analysis.wav"
    audio.write_bytes(b"")

    manifest: dict[str, Any] = {
        "analysis_audio_path": str(audio),
        "speech_audio_path": "",
        "music_audio_path": "",
    }

    job = SimpleNamespace(
        preprocessing_manifest=manifest,
        raw_video_path=None,
        profile_metadata={
            "audio": {
                "silence_threshold_db": -41,
                "min_silence_duration_ms": 500,
            }
        },
        quality_mode=None,
        profile_id=None,
        silence_threshold_db=None,
    )

    captured: dict[str, Any] = {}

    def fake_detect(source_path: str, threshold_db: float, min_duration_seconds: float, **kwargs: Any) -> SilenceDetectionResult:
        captured["source_path"] = source_path
        captured["threshold_db"] = threshold_db
        captured["min_duration_seconds"] = min_duration_seconds
        return _make_ok_detection(source_path, threshold_db, min_duration_seconds)

    monkeypatch.setattr(runner_module, "detect_silence", fake_detect)

    report = run_silence_detection_for_job(job=job)

    assert report.status == "ok"
    assert report.source_type == "analysis_audio"
    assert report.threshold_db == -41.0
    assert report.min_duration_seconds == pytest.approx(0.5, abs=1e-9)
    assert captured["threshold_db"] == -41.0
    assert captured["min_duration_seconds"] == pytest.approx(0.5, abs=1e-9)


def test_runner_does_not_crash_on_empty_job(monkeypatch: pytest.MonkeyPatch) -> None:
    job = SimpleNamespace()

    def fake_detect(*args: Any, **kwargs: Any) -> SilenceDetectionResult:
        raise AssertionError("detect_silence should not be called for empty job")

    monkeypatch.setattr(runner_module, "detect_silence", fake_detect)

    report = run_silence_detection_for_job(job=job)

    assert isinstance(report, SilenceDetectionRunReport)
    assert report.status in ("skipped_no_audio_source", "blocked")


def test_runner_passes_threshold_and_duration_to_detector(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = tmp_path / "analysis.wav"
    audio.write_bytes(b"")

    manifest: dict[str, Any] = {
        "analysis_audio_path": str(audio),
        "speech_audio_path": "",
        "music_audio_path": "",
    }

    overrides: dict[str, Any] = {
        "threshold_db": -37.5,
        "min_duration_seconds": 0.6,
    }

    captured: dict[str, Any] = {}

    def fake_detect(source_path: str, threshold_db: float, min_duration_seconds: float, **kwargs: Any) -> SilenceDetectionResult:
        captured["source_path"] = source_path
        captured["threshold_db"] = threshold_db
        captured["min_duration_seconds"] = min_duration_seconds
        return _make_ok_detection(source_path, threshold_db, min_duration_seconds)

    monkeypatch.setattr(runner_module, "detect_silence", fake_detect)

    report = build_silence_detection_run_report(
        preprocessing_manifest=manifest,
        overrides=overrides,
    )

    assert report.status == "ok"
    assert captured["threshold_db"] == -37.5
    assert captured["min_duration_seconds"] == pytest.approx(0.6, abs=1e-9)
    assert report.threshold_db == -37.5
    assert report.min_duration_seconds == pytest.approx(0.6, abs=1e-9)


# ---------------------------------------------------------------------------
# BOM / Newline hygiene
# ---------------------------------------------------------------------------

def test_silence_detection_runner_files_have_no_bom_and_end_with_newline() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    files = [
        repo_root / "models" / "silence_detection_run.py",
        repo_root / "core" / "silence_detection_runner.py",
        repo_root / "tests" / "test_silence_detection_runner_smoke.py",
    ]
    for fpath in files:
        raw = fpath.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {fpath}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {fpath}"
