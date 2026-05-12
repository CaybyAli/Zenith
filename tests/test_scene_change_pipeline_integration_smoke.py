from __future__ import annotations

from pathlib import Path
import re


GAMING_PIPELINE_PATH = Path("core/gaming_pipeline.py")
JOB_MODEL_PATH = Path("models/job.py")
TEST_FILE_PATH = Path("tests/test_scene_change_pipeline_integration_smoke.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_gaming_pipeline_imports_scene_change_runner_functions() -> None:
    content = _read(GAMING_PIPELINE_PATH)

    assert "from core.scene_change_runner import (" in content
    assert "apply_scene_change_run_report_to_job" in content
    assert "run_scene_change_for_job" in content


def test_gaming_pipeline_contains_scene_change_decision_events() -> None:
    content = _read(GAMING_PIPELINE_PATH)

    assert "SCENE_CHANGE_STARTED" in content
    assert "SCENE_CHANGE_DONE" in content
    assert "SCENE_CHANGE_SKIPPED" in content
    assert "SCENE_CHANGE_BLOCKED" in content
    assert "SCENE_CHANGE_FAILED" in content


def test_gaming_pipeline_contains_scene_change_checkpoint() -> None:
    content = _read(GAMING_PIPELINE_PATH)

    assert 'step_name="scene_change_done"' in content
    assert 'reason="scene_change_detection_completed_or_skipped"' in content


def test_gaming_pipeline_scene_change_block_is_after_preprocessing_before_rms() -> None:
    content = _read(GAMING_PIPELINE_PATH)

    preprocessing_index = content.index('step_name="preprocessing_ready"')
    scene_change_index = content.index("Scene Change Detection (2B-13-C)")
    rms_index = content.index("RMS Energy")

    assert preprocessing_index < scene_change_index < rms_index


def test_gaming_pipeline_scene_change_block_runs_and_applies_report() -> None:
    content = _read(GAMING_PIPELINE_PATH)

    assert "scene_change_report = run_scene_change_for_job(" in content
    assert "apply_scene_change_run_report_to_job(job, scene_change_report)" in content
    assert '"pipeline_step": "scene_change_detection"' in content


def test_gaming_pipeline_scene_change_block_is_try_except_protected() -> None:
    content = _read(GAMING_PIPELINE_PATH)

    start = content.index("Scene Change Detection (2B-13-C)")
    end = content.index("End Scene Change Detection")
    block = content[start:end]

    assert "try:" in block
    assert "except Exception as scene_change_exc:" in block
    assert "SCENE_CHANGE_FAILED" in block
    assert 'job.scene_change_status = "failed"' in block
    assert 'job.scene_change_recommendation = "scene_detection_failed"' in block


def test_scene_change_status_event_mapping_exists() -> None:
    content = _read(GAMING_PIPELINE_PATH)

    assert "def _scene_change_event_type_for_status" in content
    assert 'return "SCENE_CHANGE_DONE"' in content
    assert 'return "SCENE_CHANGE_SKIPPED"' in content
    assert 'return "SCENE_CHANGE_BLOCKED"' in content
    assert 'return "SCENE_CHANGE_FAILED"' in content


def test_scene_change_decision_details_contains_job_persisted_fields() -> None:
    content = _read(GAMING_PIPELINE_PATH)

    assert "def _scene_change_decision_details" in content
    assert '"scene_change_count"' in content
    assert '"hard_change_count"' in content
    assert '"soft_transition_count"' in content
    assert '"false_positive_candidate_count"' in content
    assert '"recommendation"' in content
    assert '"warnings"' in content
    assert '"errors"' in content


def test_job_model_keeps_scene_change_fields() -> None:
    content = _read(JOB_MODEL_PATH)

    expected_fields = [
        "scene_change_report",
        "scene_change_status",
        "scene_change_selected_path",
        "scene_change_selected_type",
        "scene_change_result",
        "scene_changes",
        "scene_change_count",
        "scene_change_hard_count",
        "scene_change_soft_count",
        "scene_change_false_positive_candidate_count",
        "scene_change_threshold",
        "scene_change_duration_seconds",
        "scene_change_recommendation",
    ]

    for field_name in expected_fields:
        assert field_name in content


def test_scene_change_pipeline_integration_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        GAMING_PIPELINE_PATH,
        JOB_MODEL_PATH,
        TEST_FILE_PATH,
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
