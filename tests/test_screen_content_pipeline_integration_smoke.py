from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GAMING_PIPELINE_PATH = REPO_ROOT / "core" / "gaming_pipeline.py"
JOB_MODEL_PATH = REPO_ROOT / "models" / "job.py"
THIS_TEST_PATH = REPO_ROOT / "tests" / "test_screen_content_pipeline_integration_smoke.py"


def _read_pipeline_text() -> str:
    return GAMING_PIPELINE_PATH.read_text(encoding="utf-8")


def _read_job_text() -> str:
    return JOB_MODEL_PATH.read_text(encoding="utf-8")


def test_gaming_pipeline_imports_screen_content_runner_functions():
    text = _read_pipeline_text()

    assert "from core.screen_content_runner import (" in text
    assert "apply_screen_content_run_report_to_job" in text
    assert "run_screen_content_classification_for_job" in text


def test_gaming_pipeline_contains_screen_content_decision_events():
    text = _read_pipeline_text()

    assert "SCREEN_CONTENT_STARTED" in text
    assert "SCREEN_CONTENT_DONE" in text
    assert "SCREEN_CONTENT_SKIPPED" in text
    assert "SCREEN_CONTENT_BLOCKED" in text
    assert "SCREEN_CONTENT_FAILED" in text


def test_gaming_pipeline_contains_screen_content_checkpoint():
    text = _read_pipeline_text()

    assert 'step_name="screen_content_done"' in text
    assert 'reason="screen_content_completed_or_skipped"' in text


def test_screen_content_block_is_try_except_protected():
    text = _read_pipeline_text()

    start = text.index("Screen Content Classification (2B-17-C)")
    end = text.index("End Screen Content Classification")
    block = text[start:end]

    assert "try:" in block
    assert "except Exception as screen_content_exc:" in block
    assert 'job.screen_content_status = "failed"' in block
    assert (
        'job.screen_content_recommendation = "screen_content_classification_failed"'
        in block
    )


def test_screen_content_block_runs_runner_and_applies_report():
    text = _read_pipeline_text()

    start = text.index("Screen Content Classification (2B-17-C)")
    end = text.index("End Screen Content Classification")
    block = text[start:end]

    assert (
        "screen_content_report = run_screen_content_classification_for_job(job)"
        in block
    )
    assert "apply_screen_content_run_report_to_job(job, screen_content_report)" in block


def test_screen_content_block_is_after_stutter_detection_and_before_rms_energy():
    text = _read_pipeline_text()

    stutter_detection_position = text.index("Stutter Detection (2B-16-C)")
    screen_content_position = text.index("Screen Content Classification (2B-17-C)")
    rms_energy_position = text.index("RMS Energy")

    assert stutter_detection_position < screen_content_position
    assert screen_content_position < rms_energy_position


def test_screen_content_job_fields_are_present():
    text = _read_job_text()

    required_fields = [
        "screen_content_report",
        "screen_content_status",
        "screen_content_selected_path",
        "screen_content_selected_type",
        "screen_content_result",
        "screen_content_points",
        "screen_content_segments",
        "screen_content_point_count",
        "screen_content_segment_count",
        "screen_content_gameplay_segment_count",
        "screen_content_menu_segment_count",
        "screen_content_loading_segment_count",
        "screen_content_scoreboard_segment_count",
        "screen_content_death_screen_segment_count",
        "screen_content_victory_screen_segment_count",
        "screen_content_black_screen_segment_count",
        "screen_content_duration_seconds",
        "screen_content_frame_sample_rate",
        "screen_content_recommendation",
    ]

    for field_name in required_fields:
        assert field_name in text


def test_screen_content_pipeline_test_file_has_no_bom():
    content = THIS_TEST_PATH.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")


def test_screen_content_pipeline_test_file_ends_with_newline():
    content = THIS_TEST_PATH.read_bytes()

    assert content.endswith(b"\n")
