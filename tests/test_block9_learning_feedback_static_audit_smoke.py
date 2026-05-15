from __future__ import annotations

import ast
from pathlib import Path


BLOCK9_PRODUCT_FILES = [
    Path("models/feedback_intake.py"),
    Path("core/feedback_intake.py"),
    Path("core/feedback_intake_runner.py"),
    Path("core/feedback_intake_signal_adapter.py"),
    Path("models/style_dna_feedback_update.py"),
    Path("core/style_dna_feedback_updater.py"),
    Path("core/style_dna_feedback_updater_runner.py"),
    Path("core/style_dna_feedback_updater_signal_adapter.py"),
    Path("models/style_dna_review_gate.py"),
    Path("core/style_dna_review_gate.py"),
    Path("core/style_dna_review_gate_runner.py"),
    Path("core/style_dna_review_gate_signal_adapter.py"),
    Path("models/style_dna_apply_plan.py"),
    Path("core/style_dna_apply_plan_builder.py"),
    Path("core/style_dna_apply_plan_runner.py"),
    Path("core/style_dna_apply_plan_signal_adapter.py"),
    Path("models/style_dna_persistence_gate.py"),
    Path("core/style_dna_persistence_gate.py"),
    Path("core/style_dna_persistence_gate_runner.py"),
    Path("core/style_dna_persistence_gate_signal_adapter.py"),
    Path("models/learning_pattern_recognition.py"),
    Path("core/learning_pattern_recognition.py"),
    Path("core/learning_pattern_recognition_runner.py"),
    Path("core/learning_pattern_recognition_signal_adapter.py"),
]

CENTRAL_FILES = [
    Path("models/job.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
]

BLOCK9_AUDIT_TEST_FILES = [
    Path("tests/test_block9_learning_feedback_static_audit_smoke.py"),
    Path("tests/test_block9_learning_feedback_pipeline_order_audit_smoke.py"),
    Path("tests/test_block9_learning_feedback_safety_contract_audit_smoke.py"),
    Path("tests/test_block9_learning_feedback_registry_audit_smoke.py"),
    Path("tests/test_block9_learning_feedback_job_fields_audit_smoke.py"),
    Path("tests/test_block9_learning_feedback_final_audit_smoke.py"),
]

BANNED_IMPORT_ROOTS = {
    "subprocess",
    "moviepy",
    "cv2",
    "shutil",
}

BANNED_CALL_NAMES = {
    "execute_final_cutlist",
    "apply_final_cutlist",
    "TimelineBuilder",
    "HighlightSelector",
    "RenderProcessor",
    "VideoWriter",
    "write_videofile",
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

BANNED_ATTRIBUTE_CALLS = {
    "system",
    "run",
    "Popen",
    "call",
    "check_call",
    "check_output",
    "VideoWriter",
    "write_videofile",
    "write_text",
    "write_bytes",
    "mkdir",
    "makedirs",
    "copyfile",
}

BANNED_STRING_TOKENS_FOR_BLOCK9 = {
    "execute_final_cutlist",
    "apply_final_cutlist",
    "TimelineBuilder",
    "HighlightSelector",
    "RenderProcessor",
    "moviepy",
    "cv2.VideoWriter",
    "write_videofile",
    "publish_video",
    "upload_video",
    "start_render",
    "trigger_render",
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "shell=True",
}


def _read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _dotted_call_name(node: ast.Call) -> str:
    parts = []
    func = node.func
    while isinstance(func, ast.Attribute):
        parts.append(func.attr)
        func = func.value
    if isinstance(func, ast.Name):
        parts.append(func.id)
    return ".".join(reversed(parts))


def test_all_block9_product_files_and_central_files_exist():
    missing = [str(path) for path in [*BLOCK9_PRODUCT_FILES, *CENTRAL_FILES] if not path.exists()]
    assert missing == []


def test_all_2b65_audit_test_files_exist():
    missing = [str(path) for path in BLOCK9_AUDIT_TEST_FILES if not path.exists()]
    assert missing == []


def test_block9_product_files_have_no_bom_and_end_with_newline():
    problems = []

    for path in BLOCK9_PRODUCT_FILES:
        data = _read_bytes(path)

        if data.startswith(b"\xef\xbb\xbf"):
            problems.append(f"{path}: has UTF-8 BOM")

        if data and not data.endswith(b"\n"):
            problems.append(f"{path}: does not end with newline")

    assert problems == []


def test_block9_product_files_do_not_import_dangerous_modules():
    problems = []

    for path in BLOCK9_PRODUCT_FILES:
        tree = ast.parse(_read_text(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in BANNED_IMPORT_ROOTS:
                        problems.append(f"{path}: banned import {alias.name}")

            if isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in BANNED_IMPORT_ROOTS:
                    problems.append(f"{path}: banned import from {node.module}")

    assert problems == []


def test_block9_product_files_do_not_call_dangerous_operations():
    problems = []

    for path in BLOCK9_PRODUCT_FILES:
        tree = ast.parse(_read_text(path))

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            name = _call_name(node)
            dotted = _dotted_call_name(node)

            if name in BANNED_CALL_NAMES:
                problems.append(f"{path}: banned call {dotted or name}")

            if name in BANNED_ATTRIBUTE_CALLS and dotted.startswith(("subprocess.", "os.", "shutil.", "Path.", "path.")):
                problems.append(f"{path}: banned attribute call {dotted}")

            for keyword in node.keywords:
                if keyword.arg == "shell":
                    if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        problems.append(f"{path}: shell=True is banned")

            if dotted in {
                "subprocess.run",
                "subprocess.Popen",
                "subprocess.call",
                "subprocess.check_call",
                "subprocess.check_output",
                "os.system",
                "shutil.copyfile",
            }:
                problems.append(f"{path}: banned call {dotted}")

            if dotted in {
                "style_dna.write",
                "profile.write",
            }:
                problems.append(f"{path}: banned direct write {dotted}")

    assert problems == []


def test_block9_product_files_do_not_contain_explicit_execution_call_tokens():
    problems = []

    dangerous_text_tokens = {
        "subprocess.run(",
        "subprocess.Popen(",
        "os.system(",
        "shell=True",
        "moviepy",
        "cv2.VideoWriter(",
        "write_videofile(",
        "execute_final_cutlist(",
        "apply_final_cutlist(",
        "publish_video(",
        "upload_video(",
        "start_render(",
        "trigger_render(",
    }

    for path in BLOCK9_PRODUCT_FILES:
        text = _read_text(path)

        for token in dangerous_text_tokens:
            if token in text:
                problems.append(f"{path}: banned execution token {token}")

    assert problems == []
