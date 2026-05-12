from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GAMING_PIPELINE_PATH = REPO_ROOT / "core" / "gaming_pipeline.py"
JOB_MODEL_PATH = REPO_ROOT / "models" / "job.py"
THIS_TEST_PATH = REPO_ROOT / "tests" / "test_face_reaction_pipeline_integration_smoke.py"


def _read_pipeline_text() -> str:
    return GAMING_PIPELINE_PATH.read_text(encoding="utf-8")


def _read_job_text() -> str:
    return JOB_MODEL_PATH.read_text(encoding="utf-8")


def test_gaming_pipeline_imports_face_reaction_runner_functions():
    text = _read_pipeline_text()

    assert "from core.face_reaction_runner import (" in text
    assert "apply_face_reaction_run_report_to_job" in text
    assert "run_face_reaction_for_job" in text


def test_gaming_pipeline_contains_face_reaction_decision_events():
    text = _read_pipeline_text()

    assert "FACE_REACTION_STARTED" in text
    assert "FACE_REACTION_DONE" in text
    assert "FACE_REACTION_SKIPPED" in text
    assert "FACE_REACTION_BLOCKED" in text
    assert "FACE_REACTION_FAILED" in text


def test_gaming_pipeline_contains_face_reaction_checkpoint():
    text = _read_pipeline_text()

    assert 'step_name="face_reaction_done"' in text
    assert 'reason="face_reaction_completed_or_skipped"' in text


def test_face_reaction_block_is_try_except_protected():
    text = _read_pipeline_text()

    start = text.index("Face Reaction Analysis (2B-15-C)")
    end = text.index("End Face Reaction Analysis")
    block = text[start:end]

    assert "try:" in block
    assert "except Exception as face_reaction_exc:" in block
    assert 'job.face_reaction_status = "failed"' in block
    assert 'job.face_reaction_recommendation = "face_reaction_failed"' in block


def test_face_reaction_block_runs_runner_and_applies_report():
    text = _read_pipeline_text()

    start = text.index("Face Reaction Analysis (2B-15-C)")
    end = text.index("End Face Reaction Analysis")
    block = text[start:end]

    assert "face_reaction_report = run_face_reaction_for_job(job)" in block
    assert "apply_face_reaction_run_report_to_job(job, face_reaction_report)" in block


def test_face_reaction_block_is_after_motion_and_before_rms_energy():
    text = _read_pipeline_text()

    motion_analysis_position = text.index("Motion Analysis (2B-14-C)")
    face_reaction_position = text.index("Face Reaction Analysis (2B-15-C)")
    rms_energy_position = text.index("RMS Energy")

    assert motion_analysis_position < face_reaction_position
    assert face_reaction_position < rms_energy_position


def test_face_reaction_job_fields_are_present():
    text = _read_job_text()

    required_fields = [
        "face_reaction_report",
        "face_reaction_status",
        "face_reaction_selected_path",
        "face_reaction_selected_type",
        "face_reaction_result",
        "face_reaction_points",
        "face_reaction_segments",
        "face_reaction_point_count",
        "face_reaction_segment_count",
        "face_reaction_detected_point_count",
        "face_reaction_candidate_count",
        "face_reaction_high_segment_count",
        "face_reaction_duration_seconds",
        "face_reaction_frame_sample_rate",
        "face_reaction_recommendation",
    ]

    for field_name in required_fields:
        assert field_name in text


def test_face_reaction_pipeline_test_file_has_no_bom():
    content = THIS_TEST_PATH.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")


def test_face_reaction_pipeline_test_file_ends_with_newline():
    content = THIS_TEST_PATH.read_bytes()

    assert content.endswith(b"\n")
