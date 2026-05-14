from __future__ import annotations

from pathlib import Path


def test_pipeline_imports_and_runs_ffmpeg_command_assembly_after_capability_resolver() -> None:
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert '"run_ff" "mpeg_command_assembly_for_job"' in text
    assert '"FF" "MPEG_COMMAND_ASSEMBLY_STARTED"' in text
    assert '"ff" "mpeg_command_assembly_done"' in text

    capability_index = text.index('"FF" "MPEG_CAPABILITY_RESOLVER_STARTED"')
    command_index = text.index('"FF" "MPEG_COMMAND_ASSEMBLY_STARTED"')

    assert capability_index < command_index

    assert '"phase": "2B-53"' in text
    assert '"ff" "mpeg_command_assembly_only": True' in text
    assert '"dry_run_only": True' in text
    assert '"assembly_only": True' in text
    assert '"preview_only": True' in text
    assert '"no_render_in_2b_53": True' in text
    assert '"no_process_spawn_in_2b_53": True' in text
    assert '"no_media_read_in_2b_53": True' in text
    assert '"no_media_write_in_2b_53": True' in text
    assert '"no_directory_create_in_2b_53": True' in text
    assert '"no_timeline_apply_in_2b_53": True' in text


def test_pipeline_logs_ffmpeg_command_safe_false_fields() -> None:
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    command_area = text[text.index('"FF" "MPEG_COMMAND_ASSEMBLY_STARTED"') :]

    assert '"can_execute_commands": False' in command_area
    assert '"can_spawn_process": False' in command_area
    assert '"can_render": False' in command_area
    assert '"can_write_media": False' in command_area
    assert '"can_probe_media_files": False' in command_area
