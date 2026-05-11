from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

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


REPO_ROOT = Path(__file__).resolve().parents[1]
JOB_FILE = REPO_ROOT / "models" / "job.py"
PIPELINE_FILE = REPO_ROOT / "core" / "gaming_pipeline.py"
TEST_FILE = REPO_ROOT / "tests" / "test_audio_normalization_pipeline_integration_smoke.py"


AUDIO_NORMALIZATION_FIELDS = [
    "audio_normalization_report",
    "audio_normalization_status",
    "audio_normalization_selected_path",
    "audio_normalization_selected_type",
    "audio_normalization_source_selection",
    "audio_normalization_result",
    "audio_normalization_level_status",
    "audio_normalization_needed",
    "audio_normalization_recommendation",
    "audio_normalization_target_rms_dbfs",
    "audio_normalization_target_peak_dbfs",
    "audio_normalization_recommended_gain_db",
    "audio_normalization_limited_gain_db",
    "audio_normalization_gain_limited_by_peak",
    "audio_normalization_would_clip_after_gain",
    "audio_normalization_peak_dbfs",
    "audio_normalization_rms_dbfs",
    "audio_normalization_peak_amplitude",
    "audio_normalization_rms",
    "audio_normalization_clipping_sample_count",
    "audio_normalization_clipping_ratio",
    "audio_normalization_sample_count",
    "audio_normalization_duration_seconds",
    "audio_normalization_sample_rate",
    "audio_normalization_channels",
]


def _make_job() -> Job:
    return Job(
        job_id="job_audio_norm_pipeline_test",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="tests/fixtures/input.mp4",
        profile_id="gaming_main",
        quality_mode="balanced",
    )


def _make_old_job_dict() -> dict:
    return {
        "job_id": "old_job_without_audio_normalization",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "longform",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }


def _read_pipeline_source() -> str:
    return PIPELINE_FILE.read_text(encoding="utf-8")


def test_job_roundtrip_keeps_all_audio_normalization_fields():
    job = _make_job()

    job.audio_normalization_report = {"status": "ok", "source": "audio_normalization_runner"}
    job.audio_normalization_status = "ok"
    job.audio_normalization_selected_path = "preprocessed/job/analysis.wav"
    job.audio_normalization_selected_type = "analysis_audio"
    job.audio_normalization_source_selection = {"status": "selected"}
    job.audio_normalization_result = {"level_status": "too_quiet"}
    job.audio_normalization_level_status = "too_quiet"
    job.audio_normalization_needed = True
    job.audio_normalization_recommendation = "use_normalization_plan"
    job.audio_normalization_target_rms_dbfs = -18.0
    job.audio_normalization_target_peak_dbfs = -1.0
    job.audio_normalization_recommended_gain_db = 4.5
    job.audio_normalization_limited_gain_db = 3.0
    job.audio_normalization_gain_limited_by_peak = True
    job.audio_normalization_would_clip_after_gain = False
    job.audio_normalization_peak_dbfs = -2.0
    job.audio_normalization_rms_dbfs = -24.5
    job.audio_normalization_peak_amplitude = 0.79
    job.audio_normalization_rms = 0.05
    job.audio_normalization_clipping_sample_count = 12
    job.audio_normalization_clipping_ratio = 0.01
    job.audio_normalization_sample_count = 44100
    job.audio_normalization_duration_seconds = 1.0
    job.audio_normalization_sample_rate = 44100
    job.audio_normalization_channels = 2

    payload = job.to_dict()
    restored = Job.from_dict(payload)

    for field_name in AUDIO_NORMALIZATION_FIELDS:
        assert field_name in payload

    assert restored.audio_normalization_report == {"status": "ok", "source": "audio_normalization_runner"}
    assert restored.audio_normalization_status == "ok"
    assert restored.audio_normalization_selected_path == "preprocessed/job/analysis.wav"
    assert restored.audio_normalization_selected_type == "analysis_audio"
    assert restored.audio_normalization_source_selection == {"status": "selected"}
    assert restored.audio_normalization_result == {"level_status": "too_quiet"}
    assert restored.audio_normalization_level_status == "too_quiet"
    assert restored.audio_normalization_needed is True
    assert restored.audio_normalization_recommendation == "use_normalization_plan"
    assert restored.audio_normalization_recommended_gain_db == 4.5
    assert restored.audio_normalization_limited_gain_db == 3.0
    assert restored.audio_normalization_gain_limited_by_peak is True
    assert restored.audio_normalization_would_clip_after_gain is False
    assert restored.audio_normalization_peak_dbfs == -2.0
    assert restored.audio_normalization_rms_dbfs == -24.5
    assert restored.audio_normalization_clipping_sample_count == 12
    assert restored.audio_normalization_sample_rate == 44100
    assert restored.audio_normalization_channels == 2


def test_old_jobs_without_audio_normalization_fields_do_not_crash():
    restored = Job.from_dict(_make_old_job_dict())

    assert restored.audio_normalization_report == {}
    assert restored.audio_normalization_status is None
    assert restored.audio_normalization_selected_path is None
    assert restored.audio_normalization_selected_type is None
    assert restored.audio_normalization_source_selection == {}
    assert restored.audio_normalization_result == {}
    assert restored.audio_normalization_needed is False
    assert restored.audio_normalization_target_rms_dbfs == -18.0
    assert restored.audio_normalization_target_peak_dbfs == -1.0
    assert restored.audio_normalization_recommended_gain_db == 0.0
    assert restored.audio_normalization_clipping_sample_count == 0


def test_gaming_pipeline_contains_audio_normalization_import_and_events():
    source = _read_pipeline_source()

    assert "from core.audio_normalization_runner import run_audio_normalization_for_job" in source
    assert "AUDIO_NORMALIZATION_STARTED" in source
    assert "AUDIO_NORMALIZATION_DONE" in source
    assert "AUDIO_NORMALIZATION_COMPLETED_WITH_WARNINGS" in source
    assert "AUDIO_NORMALIZATION_BLOCKED" in source
    assert "AUDIO_NORMALIZATION_SKIPPED" in source
    assert "AUDIO_NORMALIZATION_FAILED" in source


def test_gaming_pipeline_uses_runner_function():
    source = _read_pipeline_source()

    assert "run_audio_normalization_for_job(" in source


def test_gaming_pipeline_does_not_call_low_level_audio_normalization_tools_directly():
    source = _read_pipeline_source()

    assert "analyze_wav_audio_normalization(" not in source
    assert "select_audio_normalization_source(" not in source
    assert "select_audio_normalization_source_for_job(" not in source


def test_gaming_pipeline_order_is_after_filler_and_before_analyzing():
    source = _read_pipeline_source()

    filler_index = source.index("FILLER_WORD_DETECTION_STARTED")
    energy_peak_index = source.index("ENERGY_PEAK_DETECTION_STARTED")
    audio_start_index = source.index("AUDIO_NORMALIZATION_STARTED")
    analyzing_index = source.index("STATE_ANALYZING")

    assert energy_peak_index < audio_start_index
    assert filler_index < audio_start_index
    assert audio_start_index < analyzing_index


def test_gaming_pipeline_source_contains_job_field_assignments():
    source = _read_pipeline_source()

    required_assignments = [
        "job.audio_normalization_report =",
        "job.audio_normalization_status =",
        "job.audio_normalization_selected_path =",
        "job.audio_normalization_selected_type =",
        "job.audio_normalization_source_selection =",
        "job.audio_normalization_result =",
        "job.audio_normalization_level_status =",
        "job.audio_normalization_needed =",
        "job.audio_normalization_recommendation =",
        "job.audio_normalization_recommended_gain_db =",
        "job.audio_normalization_limited_gain_db =",
        "job.audio_normalization_clipping_sample_count =",
    ]

    for assignment in required_assignments:
        assert assignment in source


def test_pipeline_like_report_sets_values_correctly_in_job():
    from core.gaming_pipeline import _apply_audio_normalization_report_to_job

    job = _make_job()
    report = SimpleNamespace(
        to_dict=lambda: {"status": "ok", "source": "audio_normalization_runner"},
        status="ok",
        selected_path="preprocessed/job/analysis.wav",
        selected_type="analysis_audio",
        source_selection={"status": "selected"},
        normalization_result={"level_status": "too_quiet"},
        level_status="too_quiet",
        normalization_needed=True,
        recommendation="use_normalization_plan",
        target_rms_dbfs=-18.0,
        target_peak_dbfs=-1.0,
        recommended_gain_db=4.5,
        limited_gain_db=3.0,
        gain_limited_by_peak=True,
        would_clip_after_gain=False,
        peak_dbfs=-2.0,
        rms_dbfs=-24.5,
        peak_amplitude=0.79,
        rms=0.05,
        clipping_sample_count=12,
        clipping_ratio=0.01,
        sample_count=44100,
        duration_seconds=1.0,
        sample_rate=44100,
        channels=2,
    )

    _apply_audio_normalization_report_to_job(job, report)

    assert job.audio_normalization_report == {"status": "ok", "source": "audio_normalization_runner"}
    assert job.audio_normalization_status == "ok"
    assert job.audio_normalization_selected_path == "preprocessed/job/analysis.wav"
    assert job.audio_normalization_selected_type == "analysis_audio"
    assert job.audio_normalization_source_selection == {"status": "selected"}
    assert job.audio_normalization_result == {"level_status": "too_quiet"}
    assert job.audio_normalization_level_status == "too_quiet"
    assert job.audio_normalization_needed is True
    assert job.audio_normalization_recommendation == "use_normalization_plan"
    assert job.audio_normalization_recommended_gain_db == 4.5
    assert job.audio_normalization_limited_gain_db == 3.0
    assert job.audio_normalization_gain_limited_by_peak is True
    assert job.audio_normalization_would_clip_after_gain is False
    assert job.audio_normalization_clipping_sample_count == 12
    assert job.audio_normalization_sample_rate == 44100
    assert job.audio_normalization_channels == 2


def test_audio_normalization_event_type_mapping_exists():
    from core.gaming_pipeline import _audio_normalization_event_type_for_status

    assert _audio_normalization_event_type_for_status("ok") == "AUDIO_NORMALIZATION_DONE"
    assert (
        _audio_normalization_event_type_for_status("completed_with_warnings")
        == "AUDIO_NORMALIZATION_COMPLETED_WITH_WARNINGS"
    )
    assert (
        _audio_normalization_event_type_for_status("blocked_missing_preprocessed_audio")
        == "AUDIO_NORMALIZATION_BLOCKED"
    )
    assert (
        _audio_normalization_event_type_for_status("skipped_unsupported_source")
        == "AUDIO_NORMALIZATION_SKIPPED"
    )
    assert (
        _audio_normalization_event_type_for_status("skipped_no_audio_source")
        == "AUDIO_NORMALIZATION_SKIPPED"
    )
    assert _audio_normalization_event_type_for_status("failed") == "AUDIO_NORMALIZATION_FAILED"


def test_bom_newline_hygiene():
    for path in [JOB_FILE, PIPELINE_FILE, TEST_FILE]:
        content = path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert content.endswith(b"\n"), f"Missing trailing newline in {path}"
