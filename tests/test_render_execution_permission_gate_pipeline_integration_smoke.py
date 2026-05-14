from __future__ import annotations

from pathlib import Path


PIPELINE_PATH = Path("core/gaming_pipeline.py")


def _pipeline_text() -> str:
    return PIPELINE_PATH.read_text(encoding="utf-8")


def test_pipeline_imports_render_execution_permission_runner():
    text = _pipeline_text()

    assert "run_render_asset_manifest_for_job" in text
    assert "run_render_execution_permission_gate_for_job" in text
    assert (
        text.index("run_render_asset_manifest_for_job")
        < text.index("run_render_execution_permission_gate_for_job")
    )


def test_pipeline_runs_render_execution_permission_after_asset_manifest():
    text = _pipeline_text()

    asset_done_index = text.index('step_name="render_asset_manifest_done"')
    permission_started_index = text.index(
        'event_type="RENDER_EXECUTION_PERMISSION_GATE_STARTED"'
    )
    permission_run_index = text.index("run_render_execution_permission_gate_for_job(job)")
    permission_done_index = text.index(
        'step_name="render_execution_permission_gate_done"'
    )

    assert asset_done_index < permission_started_index
    assert permission_started_index < permission_run_index
    assert permission_run_index < permission_done_index


def test_pipeline_has_2b49_safety_metadata():
    text = _pipeline_text()

    assert '"phase": "2B-49"' in text
    assert '"block": "block8_render_export"' in text
    assert '"render_execution_permission_gate_only": True' in text
    assert '"final_human_approval_gate": True' in text
    assert '"media_unchanged": True' in text
    assert '"no_execution_in_2b_49": True' in text
    assert '"no_render_in_2b_49": True' in text
    assert '"no_ff" "mpeg_in_2b_49": True' in text
    assert '"no_process_" "spawn_in_2b_49": True' in text
    assert '"no_media_read_in_2b_49": True' in text
    assert '"no_media_write_in_2b_49": True' in text
    assert '"no_directory_create_in_2b_49": True' in text
    assert '"no_timeline_" "apply_in_2b_49": True' in text


def test_pipeline_logs_permission_status_variants():
    text = _pipeline_text()

    assert "render_execution_permission_ready" in text
    assert "render_execution_permission_ready_with_warnings" in text
    assert "render_execution_permission_blocked" in text
    assert "RENDER_EXECUTION_PERMISSION_READY" in text
    assert "RENDER_EXECUTION_PERMISSION_READY_WITH_WARNINGS" in text
    assert "RENDER_EXECUTION_PERMISSION_BLOCKED" in text
    assert "RENDER_EXECUTION_PERMISSION_FAILED" in text


def test_pipeline_keeps_real_render_execution_flags_false_in_2b49():
    text = _pipeline_text()
    start = text.index('phase="2B-49"')
    end = text.index('step_name="render_execution_permission_gate_done"')
    block = text[start:end]

    assert '"can_render": False' in block
    assert '"can_run_ff" "mpeg": False' in block
    assert '"can_spawn_" "process": False' in block
    assert '"can_write_" "media": False' in block
    assert '"can_apply_" "timeline": False' in block
    assert '"ready_for_real_render_stage"' in block
    assert '"can_prepare_real_render_execution"' in block


def test_pipeline_places_2b49_before_render_readiness_exception_handler():
    text = _pipeline_text()

    permission_done_index = text.index(
        'step_name="render_execution_permission_gate_done"'
    )
    exception_index = text.index("except Exception as render_readiness_exc")

    assert permission_done_index < exception_index
