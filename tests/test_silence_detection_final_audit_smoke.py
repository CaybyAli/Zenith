from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import core.silence_detection_runner as runner_module
from core.silence_audio_source_selector import select_silence_audio_source
from core.silence_detection_runner import build_silence_detection_run_report
from core.silence_detector import (
    build_silencedetect_command,
    parse_silencedetect_output,
)
from core.silence_parameter_resolver import resolve_silence_detection_parameters
from models.job import Job
from models.silence_audio_source import SilenceAudioSourceSelection
from models.silence_detection import SilenceDetectionResult, SilenceSegment
from models.silence_detection_parameters import SilenceDetectionParameters
from models.silence_detection_run import SilenceDetectionRunReport
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

SILENCE_JOB_FIELDS = [
    "silence_detection_report",
    "silence_detection_result",
    "silence_detection_status",
    "silence_detection_source_path",
    "silence_detection_source_type",
    "silence_detection_threshold_db",
    "silence_detection_min_duration_seconds",
    "silence_segment_count",
    "silence_total_seconds",
]


def _make_job(**kwargs: Any) -> Job:
    defaults = dict(
        job_id="job_silence_final_audit_001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
    )
    defaults.update(kwargs)
    return Job(**defaults)


def _fake_ok_detection(
    source_path: str,
    threshold_db: float,
    min_duration_seconds: float,
    **_: Any,
) -> SilenceDetectionResult:
    seg = SilenceSegment(
        start_seconds=5.0,
        end_seconds=5.4,
        duration_seconds=0.4,
        threshold_db=threshold_db,
    )
    return SilenceDetectionResult(
        source_path=source_path,
        status="ok",
        threshold_db=threshold_db,
        min_duration_seconds=min_duration_seconds,
        segments=[seg],
        segment_count=1,
        total_silence_seconds=0.4,
    )


def _fake_failed_detection(
    source_path: str,
    threshold_db: float,
    min_duration_seconds: float,
    **_: Any,
) -> SilenceDetectionResult:
    return SilenceDetectionResult(
        source_path=source_path,
        status="failed",
        threshold_db=threshold_db,
        min_duration_seconds=min_duration_seconds,
        errors=["ffmpeg_silencedetect_failed"],
    )


# ---------------------------------------------------------------------------
# Test 1 — All model round-trips
# ---------------------------------------------------------------------------

def test_silence_detection_models_roundtrip() -> None:
    seg = SilenceSegment(
        start_seconds=1.0,
        end_seconds=1.5,
        duration_seconds=0.5,
        threshold_db=-40.0,
        source="ffmpeg_silencedetect",
        classification="long_pause",
        remove_candidate=True,
        confidence=0.9,
        warnings=["w1"],
        metadata={"extra": "x"},
    )
    seg2 = SilenceSegment.from_dict(seg.to_dict())
    assert seg2.start_seconds == 1.0
    assert seg2.remove_candidate is True
    assert seg2.metadata == {"extra": "x"}

    result = SilenceDetectionResult(
        source_path="/test.wav",
        status="ok",
        threshold_db=-40.0,
        min_duration_seconds=0.4,
        segments=[seg],
        segment_count=1,
        total_silence_seconds=0.5,
        warnings=["w"],
        errors=[],
    )
    result2 = SilenceDetectionResult.from_dict(result.to_dict())
    assert result2.status == "ok"
    assert result2.segment_count == 1
    assert result2.segments[0].duration_seconds == 0.5

    sel = SilenceAudioSourceSelection(
        selected_path="/audio/analysis.wav",
        source_type="analysis_audio",
        status="selected",
        exists=True,
        checked_paths=["/audio/analysis.wav"],
        preferred_order=["analysis_audio"],
        warnings=[],
        errors=[],
        recommendation="use_selected",
        metadata={"k": "v"},
    )
    sel2 = SilenceAudioSourceSelection.from_dict(sel.to_dict())
    assert sel2.source_type == "analysis_audio"
    assert sel2.exists is True
    assert sel2.metadata == {"k": "v"}

    params = SilenceDetectionParameters(
        threshold_db=-42.0,
        min_duration_seconds=0.35,
        require_existing_audio=False,
        source_priority=["overrides", "default"],
        profile_id="gaming_main",
        quality_mode="pro",
        resolved_from={"threshold_db": "overrides.threshold_db"},
        warnings=["w"],
        errors=[],
        metadata={"m": 1},
    )
    params2 = SilenceDetectionParameters.from_dict(params.to_dict())
    assert params2.threshold_db == -42.0
    assert params2.require_existing_audio is False
    assert params2.profile_id == "gaming_main"

    report = SilenceDetectionRunReport(
        status="ok",
        source_path="/audio/analysis.wav",
        source_type="analysis_audio",
        threshold_db=-42.0,
        min_duration_seconds=0.35,
        require_existing_audio=True,
        audio_source_selection={"status": "selected"},
        parameters={"threshold_db": -42.0},
        detection_result={"segment_count": 1},
        segment_count=1,
        total_silence_seconds=0.5,
        warnings=[],
        errors=[],
        recommendation="use_result",
        metadata={"run": "final"},
    )
    report2 = SilenceDetectionRunReport.from_dict(report.to_dict())
    assert report2.status == "ok"
    assert report2.threshold_db == -42.0
    assert report2.segment_count == 1
    assert report2.metadata == {"run": "final"}


# ---------------------------------------------------------------------------
# Test 2 — Parser + command builder foundation
# ---------------------------------------------------------------------------

def test_silence_detector_parser_and_command_foundation() -> None:
    cmd = build_silencedetect_command(
        source_path="/audio/test.wav",
        threshold_db=-40.0,
        min_duration_seconds=0.4,
    )
    assert "silencedetect" in " ".join(cmd)
    assert "-40" in " ".join(cmd) or "-40.0" in " ".join(cmd)
    assert "0.4" in " ".join(cmd)

    ffmpeg_output = (
        "[silencedetect @ 0x...] silence_start: 1.5\n"
        "[silencedetect @ 0x...] silence_end: 2.1 | silence_duration: 0.6\n"
        "[silencedetect @ 0x...] silence_start: 5.0\n"
        "[silencedetect @ 0x...] silence_end: 5.5 | silence_duration: 0.5\n"
    )
    result = parse_silencedetect_output(
        source_path="/audio/test.wav",
        output=ffmpeg_output,
        threshold_db=-40.0,
        min_duration_seconds=0.4,
        command_preview=cmd,
    )
    assert result.status == "ok"
    assert result.segment_count == 2
    assert abs(result.total_silence_seconds - 1.1) < 1e-6
    assert result.segments[0].start_seconds == pytest.approx(1.5)
    assert result.segments[1].duration_seconds == pytest.approx(0.5)

    result_empty = parse_silencedetect_output(
        source_path="/audio/test.wav",
        output="",
        threshold_db=-40.0,
        min_duration_seconds=0.4,
        command_preview=cmd,
    )
    assert result_empty.status == "ok"
    assert result_empty.segment_count == 0

    orphan_output = (
        "[silencedetect @ 0x...] silence_end: 3.0 | silence_duration: 1.0\n"
    )
    result_orphan = parse_silencedetect_output(
        source_path="/audio/test.wav",
        output=orphan_output,
        threshold_db=-40.0,
        min_duration_seconds=0.4,
        command_preview=cmd,
    )
    assert result_orphan.status == "ok"
    assert len(result_orphan.warnings) > 0


# ---------------------------------------------------------------------------
# Test 3 — Source + parameter + runner wiring
# ---------------------------------------------------------------------------

def test_silence_source_parameter_and_runner_wiring(
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
        "quality_mode": "pro",
        "audio": {
            "silence_threshold_db": -43,
            "min_silence_duration_ms": 350,
        },
    }

    captured: dict[str, Any] = {}

    def fake_detect(
        source_path: str,
        threshold_db: float,
        min_duration_seconds: float,
        **_: Any,
    ) -> SilenceDetectionResult:
        captured["source_path"] = source_path
        captured["threshold_db"] = threshold_db
        captured["min_duration_seconds"] = min_duration_seconds
        return _fake_ok_detection(source_path, threshold_db, min_duration_seconds)

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


# ---------------------------------------------------------------------------
# Test 4 — Safe failure modes
# ---------------------------------------------------------------------------

def test_silence_runner_safe_failure_modes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planned = str(tmp_path / "planned_analysis.wav")
    manifest_planned: dict[str, Any] = {
        "analysis_audio_path": planned,
        "speech_audio_path": "",
        "music_audio_path": "",
    }

    detect_count: dict[str, int] = {"n": 0}

    def counting_detect(*args: Any, **kwargs: Any) -> SilenceDetectionResult:
        detect_count["n"] += 1
        return _fake_ok_detection("x", -40.0, 0.4)

    monkeypatch.setattr(runner_module, "detect_silence", counting_detect)

    report_blocked = build_silence_detection_run_report(
        preprocessing_manifest=manifest_planned,
        overrides={"require_existing_audio": False},
    )
    assert report_blocked.status == "blocked"
    assert report_blocked.recommendation == "extract_audio_first"
    assert detect_count["n"] == 0

    report_skipped = build_silence_detection_run_report(
        preprocessing_manifest=None,
        fallback_source_path=None,
    )
    assert report_skipped.status in ("skipped_no_audio_source", "blocked")
    assert "no_silence_audio_source_available" in report_skipped.errors
    assert detect_count["n"] == 0

    existing_audio = tmp_path / "existing.wav"
    existing_audio.write_bytes(b"")
    manifest_existing: dict[str, Any] = {
        "analysis_audio_path": str(existing_audio),
        "speech_audio_path": "",
        "music_audio_path": "",
    }

    def failing_detect(source_path: str, threshold_db: float, min_duration_seconds: float, **_: Any) -> SilenceDetectionResult:
        return _fake_failed_detection(source_path, threshold_db, min_duration_seconds)

    monkeypatch.setattr(runner_module, "detect_silence", failing_detect)

    report_failed = build_silence_detection_run_report(
        preprocessing_manifest=manifest_existing,
    )
    assert report_failed.status == "failed"
    assert "ffmpeg_silencedetect_failed" in report_failed.errors


# ---------------------------------------------------------------------------
# Test 5 — Job roundtrip preserves all silence pipeline fields
# ---------------------------------------------------------------------------

def test_job_roundtrip_preserves_silence_pipeline_fields() -> None:
    job = _make_job()
    job.silence_detection_report = {"status": "ok", "segment_count": 4}
    job.silence_detection_result = {"segment_count": 4, "total_silence_seconds": 2.2}
    job.silence_detection_status = "ok"
    job.silence_detection_source_path = "/audio/analysis.wav"
    job.silence_detection_source_type = "analysis_audio"
    job.silence_detection_threshold_db = -43.0
    job.silence_detection_min_duration_seconds = 0.35
    job.silence_segment_count = 4
    job.silence_total_seconds = 2.2

    restored = Job.from_dict(job.to_dict())

    for field_name in SILENCE_JOB_FIELDS:
        assert hasattr(restored, field_name), f"Missing field: {field_name}"

    assert restored.silence_detection_status == "ok"
    assert restored.silence_detection_source_type == "analysis_audio"
    assert restored.silence_detection_threshold_db == -43.0
    assert restored.silence_detection_min_duration_seconds == 0.35
    assert restored.silence_segment_count == 4
    assert restored.silence_total_seconds == pytest.approx(2.2)
    assert restored.silence_detection_report == {"status": "ok", "segment_count": 4}
    assert restored.silence_detection_result == {
        "segment_count": 4,
        "total_silence_seconds": 2.2,
    }

    job_empty = _make_job(job_id="job_empty_silence_001")
    data_no_silence = job_empty.to_dict()
    for f in SILENCE_JOB_FIELDS:
        data_no_silence.pop(f, None)
    restored_empty = Job.from_dict(data_no_silence)
    assert restored_empty.silence_detection_status is None
    assert restored_empty.silence_segment_count == 0
    assert restored_empty.silence_total_seconds == 0.0


# ---------------------------------------------------------------------------
# Test 6 — Gaming pipeline integration contract
# ---------------------------------------------------------------------------

def test_gaming_pipeline_contains_silence_integration_contract() -> None:
    src = (REPO_ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")

    assert "from core.silence_detection_runner import run_silence_detection_for_job" in src
    assert "run_silence_detection_for_job(" in src

    assert "SILENCE_DETECTION_STARTED" in src
    assert "SILENCE_AUDIO_SOURCE_SELECTED" in src
    assert "SILENCE_PARAMETERS_RESOLVED" in src
    assert "SILENCE_DETECTION_DONE" in src
    assert "SILENCE_DETECTION_SKIPPED" in src
    assert "SILENCE_DETECTION_FAILED" in src
    assert "silence_detection_done" in src

    preprocessing_idx = src.find('step_name="preprocessing_ready"')
    silence_started_idx = src.find("SILENCE_DETECTION_STARTED")
    analyzing_idx = src.find("STATE_ANALYZING")

    assert preprocessing_idx != -1
    assert silence_started_idx != -1
    assert analyzing_idx != -1
    assert preprocessing_idx < silence_started_idx < analyzing_idx


# ---------------------------------------------------------------------------
# Test 7 — BOM / trailing newline hygiene
# ---------------------------------------------------------------------------

def test_silence_detection_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        REPO_ROOT / "models" / "silence_detection.py",
        REPO_ROOT / "core" / "silence_detector.py",
        REPO_ROOT / "models" / "silence_audio_source.py",
        REPO_ROOT / "core" / "silence_audio_source_selector.py",
        REPO_ROOT / "models" / "silence_detection_parameters.py",
        REPO_ROOT / "core" / "silence_parameter_resolver.py",
        REPO_ROOT / "models" / "silence_detection_run.py",
        REPO_ROOT / "core" / "silence_detection_runner.py",
        REPO_ROOT / "core" / "gaming_pipeline.py",
        REPO_ROOT / "tests" / "test_silence_detector_foundation_smoke.py",
        REPO_ROOT / "tests" / "test_silence_audio_source_selector_smoke.py",
        REPO_ROOT / "tests" / "test_silence_parameter_resolver_smoke.py",
        REPO_ROOT / "tests" / "test_silence_detection_runner_smoke.py",
        REPO_ROOT / "tests" / "test_silence_detection_pipeline_integration_smoke.py",
        REPO_ROOT / "tests" / "test_silence_detection_final_audit_smoke.py",
    ]
    for fpath in files:
        raw = fpath.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {fpath.name}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {fpath.name}"
