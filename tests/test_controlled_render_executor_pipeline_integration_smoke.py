from __future__ import annotations

from pathlib import Path


PIPELINE_PATH = Path("core/gaming_pipeline.py")


def _pipeline_text() -> str:
    return PIPELINE_PATH.read_text(encoding="utf-8")


def test_pipeline_imports_controlled_render_executor_runner_after_permission_gate():
    text = _pipeline_text()

    assert "run_render_execution_permission_gate_for_job" in text
    assert "run_controlled_render_executor_for_job" in text
    assert (
        text.index("run_render_execution_permission_gate_for_job")
        < text.index("run_controlled_render_executor_for_job")
    )


def test_pipeline_runs_controlled_render_executor_after_permission_gate_done():
    text = _pipeline_text()

    permission_done_index = text.index(
        'step_name="render_execution_permission_gate_done"'
    )
    controlled_started_index = text.index(
        'event_type="CONTROLLED_RENDER_EXECUTOR_STARTED"'
    )
    controlled_run_index = text.index("run_controlled_render_executor_for_job(job)")
    controlled_done_index = text.index('step_name="controlled_render_executor_done"')

    assert permission_done_index < controlled_started_index
    assert controlled_started_index < controlled_run_index
    assert controlled_run_index < controlled_done_index


def test_pipeline_has_2b50_safety_metadata():
    text = _pipeline_text()

    assert '"phase": "2B-50"' in text
    assert '"block": "block8_render_export"' in text
    assert '"controlled_render_executor_foundation": True' in text
    assert '"dry_run_only": True' in text
    assert '"media_unchanged": True' in text
    assert '"no_real_render_in_2b_50": True' in text
    assert '"no_ff" "mpeg_in_2b_50": True' in text
    assert '"no_process_" "spawn_in_2b_50": True' in text
    assert '"no_media_read_in_2b_50": True' in text
    assert '"no_media_write_in_2b_50": True' in text
    assert '"no_directory_create_in_2b_50": True' in text
    assert '"no_timeline_" "apply_in_2b_50": True' in text
    assert '"execution_steps_are_dry_run_only": True' in text


def test_pipeline_logs_controlled_render_status_variants():
    text = _pipeline_text()

    assert "controlled_render_executor_dry_run_ready" in text
    assert "controlled_render_executor_dry_run_with_warnings" in text
    assert "controlled_render_executor_blocked" in text
    assert "CONTROLLED_RENDER_EXECUTOR_DRY_RUN_READY" in text
    assert "CONTROLLED_RENDER_EXECUTOR_DRY_RUN_WITH_WARNINGS" in text
    assert "CONTROLLED_RENDER_EXECUTOR_BLOCKED" in text
    assert "CONTROLLED_RENDER_EXECUTOR_FAILED" in text


def test_pipeline_keeps_real_render_execution_flags_false_in_2b50():
    text = _pipeline_text()
    start = text.index('phase="2B-50"')
    end = text.index('step_name="controlled_render_executor_done"')
    block = text[start:end]

    assert '"real_render_allowed": False' in block
    assert '"can_execute_real_render": False' in block
    assert '"can_render": False' in block
    assert '"can_run_ff" "mpeg": False' in block
    assert '"can_spawn_" "process": False' in block
    assert '"can_write_" "media": False' in block
    assert '"output_created": False' in block
    assert '"output_path": None' in block


def test_pipeline_places_2b50_before_render_readiness_exception_handler():
    text = _pipeline_text()

    controlled_done_index = text.index('step_name="controlled_render_executor_done"')
    exception_index = text.index("except Exception as render_readiness_exc")

    assert controlled_done_index < exception_index
