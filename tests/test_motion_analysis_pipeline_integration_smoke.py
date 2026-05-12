from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GAMING_PIPELINE_PATH = REPO_ROOT / "core" / "gaming_pipeline.py"
JOB_MODEL_PATH = REPO_ROOT / "models" / "job.py"
THIS_TEST_PATH = REPO_ROOT / "tests" / "test_motion_analysis_pipeline_integration_smoke.py"


def _read_pipeline_text() -> str:
    return GAMING_PIPELINE_PATH.read_text(encoding="utf-8")


def _read_job_text() -> str:
    return JOB_MODEL_PATH.read_text(encoding="utf-8")


def test_gaming_pipeline_imports_motion_analysis_runner_functions():
    text = _read_pipeline_text()

    assert "from core.motion_analysis_runner import (" in text
    assert "apply_motion_analysis_run_report_to_job" in text
    assert "run_motion_analysis_for_job" in text


def test_gaming_pipeline_contains_motion_analysis_decision_events():
    text = _read_pipeline_text()

    assert "MOTION_ANALYSIS_STARTED" in text
    assert "MOTION_ANALYSIS_DONE" in text
    assert "MOTION_ANALYSIS_SKIPPED" in text
    assert "MOTION_ANALYSIS_BLOCKED" in text
    assert "MOTION_ANALYSIS_FAILED" in text


def test_gaming_pipeline_contains_motion_analysis_checkpoint():
    text = _read_pipeline_text()

    assert 'step_name="motion_analysis_done"' in text
    assert 'reason="motion_analysis_completed_or_skipped"' in text


def test_motion_analysis_block_is_try_except_protected():
    text = _read_pipeline_text()

    start = text.index("Motion Analysis (2B-14-C)")
    end = text.index("End Motion Analysis")
    block = text[start:end]

    assert "try:" in block
    assert "except Exception as motion_analysis_exc:" in block
    assert 'job.motion_analysis_status = "failed"' in block
    assert 'job.motion_analysis_recommendation = "motion_analysis_failed"' in block


def test_motion_analysis_block_runs_runner_and_applies_report():
    text = _read_pipeline_text()

    start = text.index("Motion Analysis (2B-14-C)")
    end = text.index("End Motion Analysis")
    block = text[start:end]

    assert "motion_analysis_report = run_motion_analysis_for_job(job)" in block
    assert "apply_motion_analysis_run_report_to_job(job, motion_analysis_report)" in block


def test_motion_analysis_block_is_after_scene_change_block():
    text = _read_pipeline_text()

    scene_change_position = text.index("Scene Change Detection (2B-13-C)")
    motion_analysis_position = text.index("Motion Analysis (2B-14-C)")
    rms_energy_position = text.index("RMS Energy")

    assert scene_change_position < motion_analysis_position
    assert motion_analysis_position < rms_energy_position


def test_motion_analysis_job_fields_are_present():
    text = _read_job_text()

    required_fields = [
        "motion_analysis_report",
        "motion_analysis_status",
        "motion_analysis_selected_path",
        "motion_analysis_selected_type",
        "motion_analysis_result",
        "motion_analysis_points",
        "motion_analysis_segments",
        "motion_analysis_point_count",
        "motion_analysis_segment_count",
        "motion_analysis_low_motion_segment_count",
        "motion_analysis_high_motion_segment_count",
        "motion_analysis_dead_visual_candidate_count",
        "motion_analysis_duration_seconds",
        "motion_analysis_frame_sample_rate",
        "motion_analysis_recommendation",
    ]

    for field_name in required_fields:
        assert field_name in text


def test_motion_analysis_pipeline_test_file_has_no_bom():
    content = THIS_TEST_PATH.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")


def test_motion_analysis_pipeline_test_file_ends_with_newline():
    content = THIS_TEST_PATH.read_bytes()

    assert content.endswith(b"\n")
