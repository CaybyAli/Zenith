from __future__ import annotations

import ast
import re
from pathlib import Path

BLOCK8_CORE_FILES = [
    Path("core/render_readiness_guard.py"),
    Path("core/render_plan_builder.py"),
    Path("core/render_command_blueprint_builder.py"),
    Path("core/render_asset_manifest_builder.py"),
    Path("core/render_execution_permission_gate.py"),
    Path("core/controlled_render_executor.py"),
    Path("core/ffmpeg_capability_resolver.py"),
    Path("core/ffmpeg_command_assembly.py"),
    Path("core/controlled_ffmpeg_execution.py"),
    Path("core/output_format_handler.py"),
    Path("core/render_verification_contract.py"),
    Path("core/render_dashboard_delivery_package_builder.py"),
]

ALLOWED_RUN_FILES = {
    Path("core/ffmpeg_capability_resolver.py"),
    Path("core/controlled_ffmpeg_execution.py"),
}

FORBIDDEN_IMPORT_OR_TEXT_TOKENS = [
    "os.system",
    "shell=True",
    "subprocess.Popen",
    "moviepy",
    "cv2.VideoWriter",
    "write_videofile",
    "TimelineBuilder",
    "HighlightSelector",
    "RenderProcessor",
    "shutil.copy",
    "shutil.move",
    "copyfile",
]

FORBIDDEN_CALLS = {
    "os.system",
    "subprocess.Popen",
    "write_videofile",
    "execute_final_cutlist",
    "apply_final_cutlist",
    "apply_timeline",
    "execute_timeline",
    "reorder_timeline",
    "move_clip",
    "split_clip",
    "merge_clip",
    "open_video",
    "read_media",
    "write_media",
    "start_render",
    "export_video",
    "extract_frame",
    "extract_thumbnail",
    "shutil.copy",
    "shutil.move",
    "shutil.copyfile",
}

FORBIDDEN_CALL_SUFFIXES = (
    ".write_text",
    ".write_bytes",
    ".rename",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return re.sub(r'["\']\s+["\']', "", text)


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _calls(path: Path) -> list[str]:
    tree = ast.parse(_text(path), filename=str(path))
    return [
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    ]


def test_no_forbidden_media_or_timeline_operations_in_block8_core_files() -> None:
    for path in BLOCK8_CORE_FILES:
        text = _normalized(_text(path))

        for token in FORBIDDEN_IMPORT_OR_TEXT_TOKENS:
            assert token not in text, f"{token} found in {path}"

        for call in _calls(path):
            assert call not in FORBIDDEN_CALLS, f"{call} found in {path}"
            assert not call.endswith(FORBIDDEN_CALL_SUFFIXES), (
                f"{call} found in {path}"
            )


def test_subprocess_run_allowlist_is_exact() -> None:
    actual = {
        path
        for path in BLOCK8_CORE_FILES
        if "subprocess.run" in _text(path)
    }

    assert actual == ALLOWED_RUN_FILES


def test_controlled_smoke_directory_creation_is_temp_or_smoke_only() -> None:
    text = _text(Path("core/controlled_ffmpeg_execution.py"))

    assert "candidate.mkdir" in text
    assert "safe_markers" in text
    assert "temp" in text
    assert "tmp" in text
    assert "smoke" in text
    assert "pytest" in text
    assert "smoke_output_dir_must_be_temp_or_smoke_path" in text


def test_ffmpeg_tool_probe_has_no_input_media_and_no_project_output() -> None:
    text = _text(Path("core/ffmpeg_capability_resolver.py"))

    assert "subprocess.run" in text
    assert "shell=False" in text
    assert "timeout=10" in text
    assert '"-i"' not in text
    assert "raw_video_path" not in text
    assert "project_output" not in text


def test_controlled_ffmpeg_smoke_has_no_user_media_or_project_output_command() -> None:
    text = _text(Path("core/controlled_ffmpeg_execution.py"))

    assert "subprocess.run" in text
    assert "shell=False" in text
    assert "lavfi" in text
    assert "testsrc" in text
    assert "sine=frequency=1000" in text
    assert "raw_video_path" not in text
    assert "source_path" not in text
    assert "project_output_path" not in text


def test_dashboard_delivery_package_remains_data_only() -> None:
    text = _normalized(_text(Path("core/render_dashboard_delivery_package_builder.py")))

    assert "write_text" not in text
    assert "write_bytes" not in text
    assert "shutil" not in text
    assert "extract_thumbnail(" not in text
    assert "can_write_dashboard_file" in text
    assert "can_move_video" in text
    assert "can_copy_output" in text
    assert "can_extract_thumbnail" in text
    assert "can_render" in text
