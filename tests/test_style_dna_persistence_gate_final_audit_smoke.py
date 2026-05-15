from __future__ import annotations

import ast
from pathlib import Path


PRODUCT_FILES = [
    "models/style_dna_persistence_gate.py",
    "core/style_dna_persistence_gate.py",
    "core/style_dna_persistence_gate_runner.py",
    "core/style_dna_persistence_gate_signal_adapter.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
    "models/job.py",
]

STRICT_NEW_FILES = [
    "models/style_dna_persistence_gate.py",
    "core/style_dna_persistence_gate.py",
    "core/style_dna_persistence_gate_runner.py",
    "core/style_dna_persistence_gate_signal_adapter.py",
]

FORBIDDEN_IMPORTS = {
    "subprocess",
    "shutil",
    "moviepy",
    "cv2",
}

FORBIDDEN_CALLS = {
    "os.system",
    "subprocess.run",
    "subprocess.Popen",
    "VideoWriter",
    "write_videofile",
    "execute_final_cutlist",
    "apply_final_cutlist",
    "apply_timeline",
    "execute_timeline",
    "reorder_timeline",
    "move_clip",
    "split_clip",
    "merge_clip",
    "write_style_dna",
    "save_style_dna",
    "update_style_dna_file",
    "update_profile",
    "change_profile",
    "publish_video",
    "upload_video",
    "autopublish",
    "start_render",
    "trigger_render",
    "write_text",
    "write_bytes",
    "mkdir",
    "makedirs",
    "backup_style_dna",
    "create_backup",
    "copyfile",
}

FORBIDDEN_CLASS_NAMES = {
    "TimelineBuilder",
    "HighlightSelector",
    "RenderProcessor",
}


def test_product_files_have_no_bom_and_end_with_newline():
    for file_name in PRODUCT_FILES:
        data = Path(file_name).read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), file_name
        assert data.endswith(b"\n"), file_name


def test_new_product_files_have_no_forbidden_imports_or_runtime_calls():
    for file_name in STRICT_NEW_FILES:
        tree = ast.parse(Path(file_name).read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".")[0]
                    assert root_name not in FORBIDDEN_IMPORTS, (
                        f"forbidden import {alias.name} found in {file_name}"
                    )

            if isinstance(node, ast.ImportFrom):
                root_name = (node.module or "").split(".")[0]
                assert root_name not in FORBIDDEN_IMPORTS, (
                    f"forbidden import from {node.module} found in {file_name}"
                )

            if isinstance(node, ast.Call):
                call_name = _call_name(node.func)
                assert call_name not in FORBIDDEN_CALLS, (
                    f"forbidden call {call_name} found in {file_name}"
                )

            if isinstance(node, ast.Name):
                assert node.id not in FORBIDDEN_CLASS_NAMES, (
                    f"forbidden class reference {node.id} found in {file_name}"
                )


def test_product_files_have_no_direct_style_dna_write_or_publish_calls():
    for file_name in PRODUCT_FILES:
        tree = ast.parse(Path(file_name).read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_name = _call_name(node.func)
                assert call_name not in FORBIDDEN_CALLS, (
                    f"forbidden call {call_name} found in {file_name}"
                )


def test_2b63_safety_metadata_is_present():
    model_text = Path("models/style_dna_persistence_gate.py").read_text(
        encoding="utf-8"
    )
    signal_text = Path("core/style_dna_persistence_gate_signal_adapter.py").read_text(
        encoding="utf-8"
    )
    pipeline_text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    for text in [model_text, signal_text]:
        assert "no_style_dna_file_write_in_2b_63" in text
        assert "no_profile_change_in_2b_63" in text
        assert "no_timeline_modify_in_2b_63" in text
        assert "no_render_trigger_in_2b_63" in text
        assert "no_publish_in_2b_63" in text

    assert "\"no_style_\" \"dna_file_write_in_2b_63\": True" in pipeline_text
    assert "\"no_profile_change_in_2b_63\": True" in pipeline_text
    assert "\"no_timeline_modify_in_2b_63\": True" in pipeline_text
    assert "\"no_\" \"render_trigger_in_2b_63\": True" in pipeline_text
    assert "\"no_publish_in_2b_63\": True" in pipeline_text


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parent = _call_name(func.value)
        if parent:
            return f"{parent}.{func.attr}"
        return func.attr
    return ""
