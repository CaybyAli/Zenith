from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GAMING_PIPELINE_PATH = REPO_ROOT / "core" / "gaming_pipeline.py"
JOB_MODEL_PATH = REPO_ROOT / "models" / "job.py"
THIS_TEST_PATH = REPO_ROOT / "tests" / "test_stutter_detection_pipeline_integration_smoke.py"


def _read_pipeline_text() -> str:
    return GAMING_PIPELINE_PATH.read_text(encoding="utf-8")


def _read_job_text() -> str:
    return JOB_MODEL_PATH.read_text(encoding="utf-8")


def test_gaming_pipeline_imports_stutter_detection_runner_functions():
    text = _read_pipeline_text()

    assert "from core.stutter_detection_runner import (" in text
    assert "apply_stutter_detection_run_report_to_job" in text
    assert "run_stutter_detection_for_job" in text


def test_gaming_pipeline_contains_stutter_detection_decision_events():
    text = _read_pipeline_text()

    assert "STUTTER_DETECTION_STARTED" in text
    assert "STUTTER_DETECTION_DONE" in text
    assert "STUTTER_DETECTION_SKIPPED" in text
    assert "STUTTER_DETECTION_BLOCKED" in text
    assert "STUTTER_DETECTION_FAILED" in text


def test_gaming_pipeline_contains_stutter_detection_checkpoint():
    text = _read_pipeline_text()

    assert 'step_name="stutter_detection_done"' in text
    assert 'reason="stutter_detection_completed_or_skipped"' in text


def test_stutter_detection_block_is_try_except_protected():
    text = _read_pipeline_text()

    start = text.index("Stutter Detection (2B-16-C)")
    end = text.index("End Stutter Detection")
    block = text[start:end]

    assert "try:" in block
    assert "except Exception as stutter_detection_exc:" in block
    assert 'job.stutter_detection_status = "failed"' in block
    assert 'job.stutter_detection_recommendation = "stutter_detection_failed"' in block


def test_stutter_detection_block_runs_runner_and_applies_report():
    text = _read_pipeline_text()

    start = text.index("Stutter Detection (2B-16-C)")
    end = text.index("End Stutter Detection")
    block = text[start:end]

    assert "stutter_detection_report = run_stutter_detection_for_job(job)" in block
    assert (
        "apply_stutter_detection_run_report_to_job(job, stutter_detection_report)"
        in block
    )


def test_stutter_detection_block_is_after_face_reaction_and_before_rms_energy():
    text = _read_pipeline_text()

    face_reaction_position = text.index("Face Reaction Analysis (2B-15-C)")
    stutter_detection_position = text.index("Stutter Detection (2B-16-C)")
    rms_energy_position = text.index("RMS Energy")

    assert face_reaction_position < stutter_detection_position
    assert stutter_detection_position < rms_energy_position


def test_stutter_detection_job_fields_are_present():
    text = _read_job_text()

    required_fields = [
        "stutter_detection_report",
        "stutter_detection_status",
        "stutter_detection_selected_path",
        "stutter_detection_selected_type",
        "stutter_detection_result",
        "stutter_detection_points",
        "stutter_detection_segments",
        "stutter_detection_point_count",
        "stutter_detection_segment_count",
        "stutter_detection_duplicate_candidate_count",
        "stutter_detection_stutter_segment_count",
        "stutter_detection_freeze_segment_count",
        "stutter_detection_duration_seconds",
        "stutter_detection_frame_sample_rate",
        "stutter_detection_recommendation",
    ]

    for field_name in required_fields:
        assert field_name in text


def test_stutter_detection_pipeline_test_file_has_no_bom():
    content = THIS_TEST_PATH.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")


def test_stutter_detection_pipeline_test_file_ends_with_newline():
    content = THIS_TEST_PATH.read_bytes()

    assert content.endswith(b"\n")
