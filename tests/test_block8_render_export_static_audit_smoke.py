from __future__ import annotations

import ast
from pathlib import Path

BLOCK8_PRODUCT_FILES = [
    Path("models/render_readiness_guard.py"),
    Path("core/render_readiness_guard.py"),
    Path("core/render_readiness_guard_runner.py"),
    Path("core/render_readiness_guard_signal_adapter.py"),
    Path("models/render_plan.py"),
    Path("core/render_plan_builder.py"),
    Path("core/render_plan_runner.py"),
    Path("core/render_plan_signal_adapter.py"),
    Path("models/render_command_blueprint.py"),
    Path("core/render_command_blueprint_builder.py"),
    Path("core/render_command_blueprint_runner.py"),
    Path("core/render_command_blueprint_signal_adapter.py"),
    Path("models/render_asset_manifest.py"),
    Path("core/render_asset_manifest_builder.py"),
    Path("core/render_asset_manifest_runner.py"),
    Path("core/render_asset_manifest_signal_adapter.py"),
    Path("models/render_execution_permission_gate.py"),
    Path("core/render_execution_permission_gate.py"),
    Path("core/render_execution_permission_gate_runner.py"),
    Path("core/render_execution_permission_gate_signal_adapter.py"),
    Path("models/controlled_render_executor.py"),
    Path("core/controlled_render_executor.py"),
    Path("core/controlled_render_executor_runner.py"),
    Path("core/controlled_render_executor_signal_adapter.py"),
    Path("models/ffmpeg_capability_resolver.py"),
    Path("core/ffmpeg_capability_resolver.py"),
    Path("core/ffmpeg_capability_resolver_runner.py"),
    Path("core/ffmpeg_capability_resolver_signal_adapter.py"),
    Path("models/ffmpeg_command_assembly.py"),
    Path("core/ffmpeg_command_assembly.py"),
    Path("core/ffmpeg_command_assembly_runner.py"),
    Path("core/ffmpeg_command_assembly_signal_adapter.py"),
    Path("models/controlled_ffmpeg_execution.py"),
    Path("core/controlled_ffmpeg_execution.py"),
    Path("core/controlled_ffmpeg_execution_runner.py"),
    Path("core/controlled_ffmpeg_execution_signal_adapter.py"),
    Path("models/output_format_contract.py"),
    Path("core/output_format_handler.py"),
    Path("core/output_format_handler_runner.py"),
    Path("core/output_format_handler_signal_adapter.py"),
    Path("models/render_verification_contract.py"),
    Path("core/render_verification_contract.py"),
    Path("core/render_verification_contract_runner.py"),
    Path("core/render_verification_contract_signal_adapter.py"),
    Path("models/render_dashboard_delivery_package.py"),
    Path("core/render_dashboard_delivery_package_builder.py"),
    Path("core/render_dashboard_delivery_package_runner.py"),
    Path("core/render_dashboard_delivery_package_signal_adapter.py"),
]

BLOCK8_AUDIT_TEST_FILES = [
    Path("tests/test_block8_render_export_static_audit_smoke.py"),
    Path("tests/test_block8_render_export_pipeline_order_audit_smoke.py"),
    Path("tests/test_block8_render_export_safety_contract_audit_smoke.py"),
    Path("tests/test_block8_render_export_registry_audit_smoke.py"),
    Path("tests/test_block8_render_export_job_fields_audit_smoke.py"),
    Path("tests/test_block8_render_export_final_audit_smoke.py"),
]

ALLOWED_SUBPROCESS_RUN_FILES = {
    Path("core/ffmpeg_capability_resolver.py"),
    Path("core/controlled_ffmpeg_execution.py"),
}

FORBIDDEN_TEXT_TOKENS = [
    "os.system",
    "shell=True",
    "subprocess.Popen",
    "write_videofile",
    "cv2.VideoWriter",
]

FORBIDDEN_CALL_NAMES = {
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

FORBIDDEN_FILE_WRITE_CALL_SUFFIXES = (
    ".write_text",
    ".write_bytes",
    ".rename",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _call_names(path: Path) -> list[str]:
    tree = ast.parse(_read(path), filename=str(path))
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            calls.append(_call_name(node.func))
    return calls


def test_all_block8_product_files_exist() -> None:
    missing = [str(path) for path in BLOCK8_PRODUCT_FILES if not path.exists()]
    assert missing == []


def test_all_2b58_audit_files_exist() -> None:
    missing = [str(path) for path in BLOCK8_AUDIT_TEST_FILES if not path.exists()]
    assert missing == []


def test_block8_product_files_have_no_bom_and_end_with_newline() -> None:
    for path in BLOCK8_PRODUCT_FILES:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"missing final newline in {path}"


def test_block8_product_files_do_not_use_forbidden_process_or_media_calls() -> None:
    for path in BLOCK8_PRODUCT_FILES:
        text = _read(path)

        for token in FORBIDDEN_TEXT_TOKENS:
            assert token not in text, f"{token} found in {path}"

        calls = _call_names(path)

        for call in calls:
            assert call not in FORBIDDEN_CALL_NAMES, f"{call} found in {path}"
            assert not call.endswith(FORBIDDEN_FILE_WRITE_CALL_SUFFIXES), (
                f"{call} found in {path}"
            )


def test_subprocess_run_is_only_in_controlled_ffmpeg_files() -> None:
    offenders = []
    for path in BLOCK8_PRODUCT_FILES:
        calls = _call_names(path)
        if "subprocess.run" in calls and path not in ALLOWED_SUBPROCESS_RUN_FILES:
            offenders.append(str(path))

    assert offenders == []


def test_ffmpeg_capability_resolver_only_runs_safe_tool_probes() -> None:
    path = Path("core/ffmpeg_capability_resolver.py")
    text = _read(path)

    assert "subprocess.run" in text
    assert "shell=False" in text
    assert "timeout=10" in text
    assert "_ALLOWED_PROBES_BY_TOOL" in text

    for token in ["-version", "-encoders", "-decoders", "-filters", "-hwaccels"]:
        assert token in text

    assert '"-i"' not in text
    assert "user_media_input" not in text
    assert "project_output_write" not in text


def test_controlled_ffmpeg_execution_only_builds_lavfi_smoke_command() -> None:
    path = Path("core/controlled_ffmpeg_execution.py")
    text = _read(path)

    assert "subprocess.run" in text
    assert "shell=False" in text
    assert "timeout_seconds: int = DEFAULT_SMOKE_TIMEOUT_SECONDS" in text
    assert "timeout=timeout_seconds" in text
    assert "lavfi" in text
    assert "testsrc" in text
    assert "sine=frequency=1000" in text
    assert "raw_video_path" not in text
    assert "user_media_input" in text
    assert "project_output" in text
    assert "no_full_render_in_2b_54" in text
