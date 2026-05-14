from __future__ import annotations

from pathlib import Path


PRODUCT_FILES = [
    Path("models/ffmpeg_command_assembly.py"),
    Path("core/ffmpeg_command_assembly.py"),
    Path("core/ffmpeg_command_assembly_runner.py"),
    Path("core/ffmpeg_command_assembly_signal_adapter.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]

FFMPEG_COMMAND_PRODUCT_FILES = [
    Path("models/ffmpeg_command_assembly.py"),
    Path("core/ffmpeg_command_assembly.py"),
    Path("core/ffmpeg_command_assembly_runner.py"),
    Path("core/ffmpeg_command_assembly_signal_adapter.py"),
]

FORBIDDEN_IN_COMMAND_PRODUCT_FILES = [
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "shell=True",
    "render_video",
    "execute_final_cutlist",
    "apply_final_cutlist",
    "TimelineBuilder",
    "HighlightSelector",
    "RenderProcessor",
    "moviepy",
    "cv2.VideoWriter",
    "write_videofile",
    "delete_media",
    "remove_file",
    "trim_now",
    "censor_now",
    "mute_track",
    "apply_timeline",
    "execute_timeline",
    "reorder_timeline",
    "move_clip",
    "split_clip",
    "merge_clip",
    "open_video",
    "read_media",
    "write_media(",
    "export_video",
    "start_render",
    "mkdir",
    "makedirs",
    "write_text",
    "write_bytes",
]

FORBIDDEN_OUTPUT_KEYS = [
    "shell_command",
    "command_line",
    "raw_command",
    "executable_command",
    "ffmpeg_command_string",
]


def test_product_files_have_no_bom_and_end_with_newline() -> None:
    for path in PRODUCT_FILES:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), path
        assert data.endswith(b"\n"), path


def test_ffmpeg_command_product_files_do_not_spawn_or_touch_media() -> None:
    for path in FFMPEG_COMMAND_PRODUCT_FILES:
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_IN_COMMAND_PRODUCT_FILES:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_ffmpeg_command_product_files_do_not_emit_shell_command_strings() -> None:
    for path in FFMPEG_COMMAND_PRODUCT_FILES:
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_OUTPUT_KEYS:
            assert forbidden not in text, f"{forbidden} found in {path}"

    model_text = Path("models/ffmpeg_command_assembly.py").read_text(encoding="utf-8")
    assert "argv_preview" in model_text
    assert "argument_tokens" in model_text
    assert "assembly_only" in model_text
    assert "preview_only" in model_text


def test_pipeline_and_registry_keep_2b_53_preview_only_flags() -> None:
    pipeline_text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    registry_text = Path("core/unified_edit_signal_registry.py").read_text(
        encoding="utf-8"
    )

    assert '"run_ff" "mpeg_command_assembly_for_job"' in pipeline_text
    assert '"FF" "MPEG_COMMAND_ASSEMBLY_STARTED"' in pipeline_text
    assert '"no_render_in_2b_53": True' in pipeline_text
    assert '"no_process_spawn_in_2b_53": True' in pipeline_text
    assert '"no_media_read_in_2b_53": True' in pipeline_text
    assert '"no_media_write_in_2b_53": True' in pipeline_text
    assert '"no_directory_create_in_2b_53": True' in pipeline_text

    assert '"build_ff" "mpeg_command_assembly_signals"' in registry_text
    assert "SOURCE_FF_COMMAND_ASSEMBLY" in registry_text


def test_ffmpeg_command_report_never_grants_real_execution_permissions() -> None:
    from core.ffmpeg_command_assembly import build_ffmpeg_command_assembly_report

    job = {
        "job_id": "audit-safe-false",
        "ffmpeg_capability_resolver_report": {"status": "ffmpeg_capability_ready"},
        "ffmpeg_capability_status": "ffmpeg_capability_ready",
        "ffmpeg_path_hint": r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
        "ffmpeg_can_prepare_real_render_tools": True,
        "render_execution_permission_report": {
            "status": "render_execution_permission_ready"
        },
        "render_execution_permission_status": "render_execution_permission_ready",
        "render_execution_ready_for_real_render_stage": True,
        "render_execution_can_prepare_real_render_execution": True,
        "render_execution_human_approved": True,
        "controlled_render_executor_report": {
            "status": "controlled_render_executor_dry_run_ready"
        },
        "controlled_render_executor_status": "controlled_render_executor_dry_run_ready",
        "controlled_render_dry_run_only": True,
        "render_blueprint_non_executable": True,
        "render_asset_paths_are_hints_only": True,
    }

    data = build_ffmpeg_command_assembly_report(job).to_dict()

    assert data["assembly_only"] is True
    assert data["preview_only"] is True
    assert data["can_execute_commands"] is False
    assert data["can_spawn_process"] is False
    assert data["can_render"] is False
    assert data["can_write_media"] is False
    assert data["can_probe_media_files"] is False
