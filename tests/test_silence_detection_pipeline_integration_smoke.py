from __future__ import annotations

from pathlib import Path

from models.job import Job
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


SILENCE_DETECTION_JOB_FIELDS = [
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


EXPECTED_PIPELINE_EVENT_NAMES = {
    "SILENCE_DETECTION_STARTED",
    "SILENCE_AUDIO_SOURCE_SELECTED",
    "SILENCE_PARAMETERS_RESOLVED",
    "SILENCE_DETECTION_DONE",
    "SILENCE_DETECTION_SKIPPED",
    "SILENCE_DETECTION_FAILED",
}


def _make_job(job_id: str = "job_silence_pipeline_integration_001") -> Job:
    return Job(
        job_id=job_id,
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


# ---------------------------------------------------------------------------
# Job-Model: round-trip
# ---------------------------------------------------------------------------

def test_job_roundtrip_preserves_silence_detection_fields() -> None:
    job = _make_job()
    job.silence_detection_report = {"status": "ok", "segment_count": 3}
    job.silence_detection_result = {"segment_count": 3, "total_silence_seconds": 1.5}
    job.silence_detection_status = "ok"
    job.silence_detection_source_path = "/audio/analysis.wav"
    job.silence_detection_source_type = "analysis_audio"
    job.silence_detection_threshold_db = -42.0
    job.silence_detection_min_duration_seconds = 0.35
    job.silence_segment_count = 3
    job.silence_total_seconds = 1.5

    data = job.to_dict()
    restored = Job.from_dict(data)

    for field_name in SILENCE_DETECTION_JOB_FIELDS:
        assert hasattr(restored, field_name), f"Job missing field: {field_name}"

    assert restored.silence_detection_report == {"status": "ok", "segment_count": 3}
    assert restored.silence_detection_result == {
        "segment_count": 3,
        "total_silence_seconds": 1.5,
    }
    assert restored.silence_detection_status == "ok"
    assert restored.silence_detection_source_path == "/audio/analysis.wav"
    assert restored.silence_detection_source_type == "analysis_audio"
    assert restored.silence_detection_threshold_db == -42.0
    assert restored.silence_detection_min_duration_seconds == 0.35
    assert restored.silence_segment_count == 3
    assert restored.silence_total_seconds == 1.5


def test_job_defaults_silence_detection_fields_are_neutral() -> None:
    job = _make_job()

    assert job.silence_detection_report == {}
    assert job.silence_detection_result == {}
    assert job.silence_detection_status is None
    assert job.silence_detection_source_path is None
    assert job.silence_detection_source_type is None
    assert job.silence_detection_threshold_db is None
    assert job.silence_detection_min_duration_seconds is None
    assert job.silence_segment_count == 0
    assert job.silence_total_seconds == 0.0


def test_job_from_dict_does_not_crash_when_silence_fields_missing() -> None:
    job = _make_job()
    data = job.to_dict()
    for field_name in SILENCE_DETECTION_JOB_FIELDS:
        data.pop(field_name, None)

    restored = Job.from_dict(data)

    for field_name in SILENCE_DETECTION_JOB_FIELDS:
        assert hasattr(restored, field_name)
    assert restored.silence_detection_status is None
    assert restored.silence_segment_count == 0


def test_apply_pipeline_like_silence_report_sets_expected_job_fields() -> None:
    from models.silence_detection_run import SilenceDetectionRunReport

    report = SilenceDetectionRunReport(
        status="ok",
        source_path="/audio/analysis.wav",
        source_type="analysis_audio",
        threshold_db=-42.0,
        min_duration_seconds=0.35,
        require_existing_audio=True,
        audio_source_selection={"status": "selected", "exists": True},
        parameters={"resolved_from": {"threshold_db": "profile.audio.silence_threshold_db"}},
        detection_result={"segment_count": 2, "total_silence_seconds": 1.0},
        segment_count=2,
        total_silence_seconds=1.0,
        warnings=[],
        errors=[],
        recommendation="use_result",
    )

    job = _make_job()
    job.silence_detection_report = report.to_dict()
    job.silence_detection_result = dict(report.detection_result or {})
    job.silence_detection_status = report.status
    job.silence_detection_source_path = report.source_path
    job.silence_detection_source_type = report.source_type
    job.silence_detection_threshold_db = report.threshold_db
    job.silence_detection_min_duration_seconds = report.min_duration_seconds
    job.silence_segment_count = int(report.segment_count)
    job.silence_total_seconds = float(report.total_silence_seconds)

    restored = Job.from_dict(job.to_dict())

    assert restored.silence_detection_status == "ok"
    assert restored.silence_detection_source_type == "analysis_audio"
    assert restored.silence_detection_threshold_db == -42.0
    assert restored.silence_segment_count == 2
    assert restored.silence_total_seconds == 1.0
    assert restored.silence_detection_report["status"] == "ok"
    assert restored.silence_detection_result.get("segment_count") == 2


# ---------------------------------------------------------------------------
# Pipeline source code: events + runner wiring
# ---------------------------------------------------------------------------

def test_gaming_pipeline_contains_silence_detection_events() -> None:
    src = (REPO_ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")

    assert "SILENCE_DETECTION_STARTED" in src
    assert "SILENCE_AUDIO_SOURCE_SELECTED" in src
    assert "SILENCE_PARAMETERS_RESOLVED" in src
    assert "SILENCE_DETECTION_DONE" in src
    assert ("SILENCE_DETECTION_SKIPPED" in src) or ("SILENCE_DETECTION_FAILED" in src)


def test_silence_detection_pipeline_integration_uses_runner_import() -> None:
    src = (REPO_ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")

    assert "from core.silence_detection_runner import run_silence_detection_for_job" in src
    assert "run_silence_detection_for_job(" in src


def test_silence_detection_persists_after_preprocessing_ready() -> None:
    src = (REPO_ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")

    preprocessing_idx = src.find('step_name="preprocessing_ready"')
    silence_started_idx = src.find("SILENCE_DETECTION_STARTED")
    analyzing_idx = src.find("STATE_ANALYZING")

    assert preprocessing_idx != -1, "preprocessing_ready checkpoint missing"
    assert silence_started_idx != -1, "SILENCE_DETECTION_STARTED missing"
    assert analyzing_idx != -1, "STATE_ANALYZING missing"
    assert preprocessing_idx < silence_started_idx < analyzing_idx, (
        "Silence detection must run between preprocessing_ready and STATE_ANALYZING"
    )


def test_silence_detection_checkpoint_step_name_present() -> None:
    src = (REPO_ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")
    assert "silence_detection_done" in src


# ---------------------------------------------------------------------------
# Hygiene
# ---------------------------------------------------------------------------

def test_pipeline_integration_files_have_no_bom_and_end_with_newline() -> None:
    no_bom_files = [
        REPO_ROOT / "models" / "job.py",
        REPO_ROOT / "tests" / "test_silence_detection_pipeline_integration_smoke.py",
    ]
    newline_only_files = [
        REPO_ROOT / "core" / "gaming_pipeline.py",
    ]
    for fpath in no_bom_files:
        raw = fpath.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {fpath}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {fpath}"
    for fpath in newline_only_files:
        raw = fpath.read_bytes()
        assert raw.endswith(b"\n"), f"Missing trailing newline in {fpath}"
