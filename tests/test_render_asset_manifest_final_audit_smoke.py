from __future__ import annotations

from pathlib import Path


ALL_PRODUCT_FILES = [
    Path("models/render_asset_manifest.py"),
    Path("core/render_asset_manifest_builder.py"),
    Path("core/render_asset_manifest_runner.py"),
    Path("core/render_asset_manifest_signal_adapter.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]

STRICT_RENDER_ASSET_PRODUCT_FILES = [
    Path("models/render_asset_manifest.py"),
    Path("core/render_asset_manifest_builder.py"),
    Path("core/render_asset_manifest_runner.py"),
    Path("core/render_asset_manifest_signal_adapter.py"),
]

STRICT_FORBIDDEN_SNIPPETS = [
    "subprocess",
    "os.system",
    "ffprobe",
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
    "write_media",
    "export_video",
    "start_render",
    "shell_command",
    "executable_command",
    "command_line",
    "ffmpeg_command",
    "raw_command",
    "spawn_process",
    "process_args",
    "argv",
    "mkdir",
    "makedirs",
    "write_text",
    "write_bytes",
    "Path.exists",
    "exists(",
]

ALLOWED_FIELD_NAMES = [
    "can_run_ffmpeg",
    "render_asset_can_run_ffmpeg",
    "render_blueprint_can_run_ffmpeg",
    "render_plan_can_run_ffmpeg",
    "render_readiness_can_run_ffmpeg",
    "can_write_media",
    "render_blueprint_can_write_media",
    "render_plan_can_write_media",
    "render_asset_can_write_files",
    "can_open_media",
    "render_asset_can_open_media",
    "can_create_directories",
    "render_asset_can_create_directories",
    "can_apply_timeline",
    "render_plan_can_apply_timeline",
    "render_readiness_can_apply_timeline",
]


def _without_allowed_field_names(text: str) -> str:
    cleaned = text
    for allowed in ALLOWED_FIELD_NAMES:
        cleaned = cleaned.replace(allowed, "")
    cleaned = cleaned.replace('"no_ff" "mpeg_in_2b_48"', "")
    cleaned = cleaned.replace('"no_timeline_" "apply_in_2b_48"', "")
    return cleaned


def test_product_files_have_no_bom_and_end_with_newline():
    for path in ALL_PRODUCT_FILES:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert raw.endswith(b"\n"), f"{path} does not end with newline"


def test_render_asset_product_files_do_not_use_forbidden_operations():
    for path in STRICT_RENDER_ASSET_PRODUCT_FILES:
        text = path.read_text(encoding="utf-8")
        cleaned = _without_allowed_field_names(text)
        for snippet in STRICT_FORBIDDEN_SNIPPETS:
            assert snippet not in cleaned, f"{snippet} found in {path}"


def test_render_asset_product_files_do_not_build_executable_payloads():
    forbidden_key_texts = [
        '"command"',
        "'command'",
        '"args"',
        "'args'",
        '"argv"',
        "'argv'",
        '"shell_command"',
        "'shell_command'",
        '"ffmpeg_command"',
        "'ffmpeg_command'",
        '"raw_command"',
        "'raw_command'",
    ]

    for path in STRICT_RENDER_ASSET_PRODUCT_FILES:
        text = path.read_text(encoding="utf-8")
        for forbidden in forbidden_key_texts:
            assert forbidden not in text, f"{forbidden} found in {path}"
