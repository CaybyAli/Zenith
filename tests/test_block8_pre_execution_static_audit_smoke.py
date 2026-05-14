from __future__ import annotations

import ast
import re
from pathlib import Path


BLOCK8_PRODUCT_FILES = [
    "models/render_readiness_guard.py",
    "core/render_readiness_guard.py",
    "core/render_readiness_guard_runner.py",
    "core/render_readiness_guard_signal_adapter.py",
    "models/render_plan.py",
    "core/render_plan_builder.py",
    "core/render_plan_runner.py",
    "core/render_plan_signal_adapter.py",
    "models/render_command_blueprint.py",
    "core/render_command_blueprint_builder.py",
    "core/render_command_blueprint_runner.py",
    "core/render_command_blueprint_signal_adapter.py",
    "models/render_asset_manifest.py",
    "core/render_asset_manifest_builder.py",
    "core/render_asset_manifest_runner.py",
    "core/render_asset_manifest_signal_adapter.py",
    "models/render_execution_permission_gate.py",
    "core/render_execution_permission_gate.py",
    "core/render_execution_permission_gate_runner.py",
    "core/render_execution_permission_gate_signal_adapter.py",
    "models/controlled_render_executor.py",
    "core/controlled_render_executor.py",
    "core/controlled_render_executor_runner.py",
    "core/controlled_render_executor_signal_adapter.py",
]

FORBIDDEN_IMPORTS = {"subprocess", "moviepy", "cv2"}
FORBIDDEN_OS_CALLS = {"system", "popen", "spawn", "spawnv", "spawnve"}
FORBIDDEN_SUBPROCESS_CALLS = {"run", "call", "check_call", "check_output", "Popen"}
FORBIDDEN_FILE_CALLS = {"mkdir", "makedirs", "write_text", "write_bytes", "unlink", "remove", "rmdir", "exists"}

FORBIDDEN_RAW_TOKENS = [
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
    "process_args",
    " argv",
]

HARD_MEDIA_PATH_RE = re.compile(
    r"([A-Za-z]:\\\\[^\\n\\r]+\\.(mp4|mov|mkv|avi|wav|mp3)|/[^\\n\\r]+\\.(mp4|mov|mkv|avi|wav|mp3))",
    re.IGNORECASE,
)


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_all_block8_product_files_exist() -> None:
    missing = [path for path in BLOCK8_PRODUCT_FILES if not Path(path).is_file()]
    assert missing == []


def test_block8_product_files_have_no_bom_and_end_with_newline() -> None:
    bad = []
    for rel in BLOCK8_PRODUCT_FILES:
        raw = Path(rel).read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            bad.append(f"{rel}:bom")
        if not raw.endswith((b"\n", b"\r\n")):
            bad.append(f"{rel}:missing_newline")
    assert bad == []


def test_block8_product_files_do_not_import_or_call_execution_apis() -> None:
    violations = []

    for rel in BLOCK8_PRODUCT_FILES:
        tree = ast.parse(_read(rel), filename=rel)

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif node.module:
                    names = [node.module.split(".")[0]]

                for name in names:
                    if name in FORBIDDEN_IMPORTS:
                        violations.append(f"{rel}: forbidden import {name}")

            if isinstance(node, ast.Call):
                func = node.func

                if isinstance(func, ast.Attribute):
                    attr = func.attr

                    if isinstance(func.value, ast.Name):
                        owner = func.value.id
                        if owner == "os" and attr in FORBIDDEN_OS_CALLS:
                            violations.append(f"{rel}: os.{attr} call")
                        if owner == "subprocess" and attr in FORBIDDEN_SUBPROCESS_CALLS:
                            violations.append(f"{rel}: subprocess.{attr} call")

                    if attr in FORBIDDEN_FILE_CALLS:
                        violations.append(f"{rel}: file-system call .{attr}()")

                if isinstance(func, ast.Name):
                    if func.id in {"open_video", "read_media", "write_media", "export_video", "start_render"}:
                        violations.append(f"{rel}: forbidden call {func.id}()")

    assert violations == []


def test_block8_product_files_do_not_contain_hard_media_paths() -> None:
    violations = []

    for rel in BLOCK8_PRODUCT_FILES:
        text = _read(rel)

        if HARD_MEDIA_PATH_RE.search(text):
            violations.append(f"{rel}: hard media path")

    assert violations == []


def test_block8_contract_metadata_tokens_exist_in_product_files() -> None:
    combined = "\n".join(_read(path) for path in BLOCK8_PRODUCT_FILES)

    required_tokens = [
        "block8_render_export",
        "no_render_in_2b_45",
        "no_render_in_2b_46",
        "no_render_in_2b_47",
        "no_render_in_2b_48",
        "no_render_in_2b_49",
        "no_real_render_in_2b_50",
        "media_unchanged",
        "dry_run_only",
        "non_executable",
        "paths_are_hints_only",
        "final_human_approval_gate",
        "execution_steps_are_dry_run_only",
    ]

    missing = [token for token in required_tokens if token not in combined]
    assert missing == []
