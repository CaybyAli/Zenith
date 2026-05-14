from __future__ import annotations

from pathlib import Path


def test_pipeline_imports_controlled_ffmpeg_execution_runner():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert "run_controlled_ff_exec_for_job" in text
    assert '"CONTROLLED_FF" "MPEG_EXECUTION_STARTED"' in text
    assert '"controlled_" "ff" "mpeg_execution_done"' in text


def test_pipeline_order_runs_after_ffmpeg_command_assembly():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    command_pos = text.index('step_name="ff" "mpeg_command_assembly_done"')
    controlled_pos = text.index('step_name="controlled_" "ff" "mpeg_execution_done"')

    assert command_pos < controlled_pos


def test_pipeline_metadata_keeps_full_render_locked():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    controlled_pos = text.index('"CONTROLLED_FF" "MPEG_EXECUTION_STARTED"')
    area = text[controlled_pos : controlled_pos + 6000]

    assert '"phase": "2B-54"' in area
    assert '"block": "block8_render_export"' in area
    assert '"controlled_" "ff" "mpeg_execution_gate": True' in area
    assert '"default_dry_run": True' in area
    assert '"smoke_test_only_when_explicitly_allowed": True' in area
    assert '"no_full_render_in_2b_54": True' in area
    assert '"no_user_media_input_in_2b_54": True' in area
    assert '"no_project_output_in_2b_54": True' in area
    assert '"no_timeline_apply_in_2b_54": True' in area
    assert '"can_execute_full_render": False' in area
    assert '"can_render_timeline": False' in area
    assert '"can_process_user_media": False' in area
    assert '"can_write_project_output": False' in area
