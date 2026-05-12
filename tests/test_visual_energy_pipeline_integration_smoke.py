from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GAMING_PIPELINE_PATH = REPO_ROOT / "core" / "gaming_pipeline.py"
JOB_MODEL_PATH = REPO_ROOT / "models" / "job.py"
THIS_TEST_PATH = REPO_ROOT / "tests" / "test_visual_energy_pipeline_integration_smoke.py"


def _read_pipeline_text() -> str:
    return GAMING_PIPELINE_PATH.read_text(encoding="utf-8")


def _read_job_text() -> str:
    return JOB_MODEL_PATH.read_text(encoding="utf-8")


def test_gaming_pipeline_imports_visual_energy_runner_functions() -> None:
    text = _read_pipeline_text()

    assert "from core.visual_energy_runner import (" in text
    assert "apply_visual_energy_run_report_to_job" in text
    assert "run_visual_energy_for_job" in text


def test_gaming_pipeline_contains_visual_energy_decision_events() -> None:
    text = _read_pipeline_text()

    assert "VISUAL_ENERGY_STARTED" in text
    assert "VISUAL_ENERGY_DONE" in text
    assert "VISUAL_ENERGY_SKIPPED" in text
    assert "VISUAL_ENERGY_FAILED" in text


def test_gaming_pipeline_contains_visual_energy_checkpoint() -> None:
    text = _read_pipeline_text()

    assert 'step_name="visual_energy_done"' in text
    assert 'reason="visual_energy_completed_or_skipped"' in text


def test_visual_energy_block_is_try_except_protected() -> None:
    text = _read_pipeline_text()

    start = text.index("Visual Energy Score (2B-18-C)")
    end = text.index("End Visual Energy Score")
    block = text[start:end]

    assert "try:" in block
    assert "except Exception as visual_energy_exc:" in block
    assert 'job.visual_energy_status = "failed"' in block
    assert 'job.visual_energy_recommendation = "visual_energy_failed"' in block


def test_visual_energy_block_runs_runner_and_applies_report() -> None:
    text = _read_pipeline_text()

    start = text.index("Visual Energy Score (2B-18-C)")
    end = text.index("End Visual Energy Score")
    block = text[start:end]

    assert "visual_energy_report = run_visual_energy_for_job(job)" in block
    assert "apply_visual_energy_run_report_to_job(job, visual_energy_report)" in block


def test_visual_energy_block_is_after_screen_content_and_before_rms_energy() -> None:
    text = _read_pipeline_text()

    screen_content_position = text.index("Screen Content Classification (2B-17-C)")
    visual_energy_position = text.index("Visual Energy Score (2B-18-C)")
    rms_energy_position = text.index("RMS Energy")

    assert screen_content_position < visual_energy_position
    assert visual_energy_position < rms_energy_position


def test_visual_energy_job_fields_are_present() -> None:
    text = _read_job_text()

    required_fields = [
        "visual_energy_report",
        "visual_energy_status",
        "visual_energy_result",
        "visual_energy_points",
        "visual_energy_segments",
        "visual_energy_point_count",
        "visual_energy_segment_count",
        "visual_energy_high_segment_count",
        "visual_energy_low_segment_count",
        "visual_energy_technical_warning_segment_count",
        "visual_energy_duration_seconds",
        "visual_energy_frame_sample_rate",
        "visual_energy_recommendation",
    ]

    for field_name in required_fields:
        assert field_name in text


def test_visual_energy_pipeline_mentions_source_statuses() -> None:
    text = _read_pipeline_text()

    start = text.index("Visual Energy Score (2B-18-C)")
    end = text.index("End Visual Energy Score")
    block = text[start:end]

    required_status_fields = [
        "scene_change_status",
        "motion_analysis_status",
        "face_reaction_status",
        "stutter_detection_status",
        "screen_content_status",
    ]

    for field_name in required_status_fields:
        assert field_name in block


def test_visual_energy_pipeline_does_not_make_cut_or_remove_decision() -> None:
    text = _read_pipeline_text()

    start = text.index("Visual Energy Score (2B-18-C)")
    end = text.index("End Visual Energy Score")
    block = text[start:end]

    forbidden_terms = [
        "remove_now",
        "hard_remove",
        "auto_remove",
        "auto_highlight",
        "force_cut",
        "apply_cut",
    ]

    for forbidden_term in forbidden_terms:
        assert forbidden_term not in block


def test_visual_energy_pipeline_test_file_has_no_bom() -> None:
    content = THIS_TEST_PATH.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")


def test_visual_energy_pipeline_test_file_ends_with_newline() -> None:
    content = THIS_TEST_PATH.read_bytes()

    assert content.endswith(b"\n")
