from __future__ import annotations

from pathlib import Path


def test_pipeline_imports_and_runs_blueprint_after_render_plan():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert "run_render_plan_for_job" in text
    assert "run_render_command_blueprint_for_job" in text
    assert text.index("run_render_plan_for_job") < text.index(
        "run_render_command_blueprint_for_job"
    )
    assert 'phase="2B-47"' in text
    assert "RENDER_COMMAND_BLUEPRINT_STARTED" in text
    assert "render_command_blueprint_done" in text


def test_pipeline_keeps_2b47_non_executable_metadata():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert '"render_command_blueprint_only": True' in text
    assert '"dry_run_only": True' in text
    assert '"non_executable": True' in text
    assert '"renderer_contract_only": True' in text
    assert '"media_unchanged": True' in text
    assert '"no_execution_in_2b_47": True' in text
    assert '"no_render_in_2b_47": True' in text
    assert '"no_process_spawn_in_2b_47": True' in text
    assert '"no_media_write_in_2b_47": True' in text

