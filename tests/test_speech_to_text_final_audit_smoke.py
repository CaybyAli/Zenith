from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from core.transcript_runner import detect_transcript_cache_status
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _read(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def test_all_speech_to_text_core_files_exist() -> None:
    required_files = [
        "core/transcript_source_selector.py",
        "core/transcript_processor.py",
        "core/transcript_runner.py",
        "core/transcript_segment_normalizer.py",
        "models/transcript_result.py",
        "models/transcript_run.py",
    ]

    for relative_path in required_files:
        assert _path(relative_path).is_file(), f"Missing STT file: {relative_path}"


def test_all_2b19_tests_exist() -> None:
    required_tests = [
        "tests/test_speech_to_text_lifeline_audit_smoke.py",
        "tests/test_transcript_segment_normalizer_smoke.py",
        "tests/test_transcript_runner_normalizer_integration_smoke.py",
        "tests/test_transcript_word_count_cache_safety_smoke.py",
        "tests/test_transcript_real_word_level_probe_smoke.py",
        "tests/test_speech_to_text_final_audit_smoke.py",
    ]

    for relative_path in required_tests:
        assert _path(relative_path).is_file(), f"Missing 2B-19 test: {relative_path}"


def test_job_has_required_transcript_fields() -> None:
    field_names = {field.name for field in fields(Job)}

    required_fields = {
        "transcript_report",
        "transcript_status",
        "transcript_segments",
        "transcript_text",
        "transcript_segment_count",
        "transcript_normalized_segment_count",
        "transcript_valid_segment_count",
        "transcript_invalid_segment_count",
        "transcript_word_count",
        "transcript_normalized_word_count",
        "transcript_word_timestamp_count",
        "transcript_has_word_level_timestamps",
        "transcript_segment_normalization_status",
        "transcript_segment_normalization_recommendation",
    }

    missing = required_fields - field_names
    assert not missing, f"Missing Job transcript fields: {sorted(missing)}"


def test_old_job_dict_loads_with_transcript_defaults() -> None:
    old_data = {
        "job_id": "legacy_stt_final_audit",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }

    job = Job.from_dict(old_data)

    assert job.transcript_report == {}
    assert job.transcript_status is None
    assert job.transcript_segments == []
    assert job.transcript_text == ""
    assert job.transcript_segment_count == 0
    assert job.transcript_normalized_segment_count == 0
    assert job.transcript_valid_segment_count == 0
    assert job.transcript_invalid_segment_count == 0
    assert job.transcript_word_count == 0
    assert job.transcript_normalized_word_count == 0
    assert job.transcript_word_timestamp_count == 0
    assert job.transcript_has_word_level_timestamps is False
    assert job.transcript_segment_normalization_status is None
    assert job.transcript_segment_normalization_recommendation is None


def test_pipeline_contains_transcript_events_and_checkpoint() -> None:
    source = _read("core/gaming_pipeline.py")

    required_strings = [
        "TRANSCRIPT_STARTED",
        "TRANSCRIPT_DONE",
        "TRANSCRIPT_SKIPPED",
        "TRANSCRIPT_BLOCKED",
        "TRANSCRIPT_FAILED",
        "transcript_done",
    ]

    for required in required_strings:
        assert required in source


def test_transcript_pipeline_runs_before_filler_word_detection() -> None:
    source = _read("core/gaming_pipeline.py")

    transcript_index = source.find("TRANSCRIPT_STARTED")
    filler_index = source.find("FILLER_WORD_DETECTION_STARTED")

    assert transcript_index != -1
    assert filler_index != -1
    assert transcript_index < filler_index


def test_runner_uses_normalizer_and_cache_safety_helper() -> None:
    source = _read("core/transcript_runner.py")

    assert "from core.transcript_segment_normalizer import normalize_transcript_segments" in source
    assert "normalize_transcript_segments(" in source
    assert "def detect_transcript_cache_status" in source


def test_cache_safety_is_explicitly_not_configured() -> None:
    job = Job(
        job_id="cache_audit_job",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="video.mp4",
    )

    cache_status = detect_transcript_cache_status(job)

    assert cache_status["status"] == "cache_not_configured"
    assert cache_status["recommendation"] == "transcript_cache_not_configured"
    assert "transcript_cache_not_configured" in cache_status["warnings"]
    assert cache_status["errors"] == []
    assert cache_status["status"] != "cache_available"
    assert "cache_path" not in cache_status


def test_transcript_files_do_not_contain_cut_or_highlight_logic() -> None:
    checked_files = [
        "core/transcript_processor.py",
        "core/transcript_runner.py",
        "core/transcript_segment_normalizer.py",
        "models/transcript_run.py",
        "models/job.py",
    ]

    forbidden_strings = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "cut_sentence_now",
        "auto_highlight",
        "force_sentence_cut",
    ]

    for relative_path in checked_files:
        source = _read(relative_path)
        for forbidden in forbidden_strings:
            assert forbidden not in source, f"{forbidden} found in {relative_path}"


def test_stt_files_have_no_bom_and_end_with_newline() -> None:
    checked_files = [
        "core/transcript_source_selector.py",
        "core/transcript_processor.py",
        "core/transcript_runner.py",
        "core/transcript_segment_normalizer.py",
        "models/transcript_result.py",
        "models/transcript_run.py",
        "models/job.py",
        "tests/test_transcript_real_word_level_probe_smoke.py",
        "tests/test_speech_to_text_final_audit_smoke.py",
    ]

    for relative_path in checked_files:
        data = _path(relative_path).read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{relative_path} has UTF-8 BOM"
        assert data.endswith(b"\n"), f"{relative_path} must end with newline"
