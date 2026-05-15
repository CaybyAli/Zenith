from pathlib import Path


AUDIT_TEST_FILES = [
    Path("tests/test_block9_learning_feedback_static_audit_smoke.py"),
    Path("tests/test_block9_learning_feedback_pipeline_order_audit_smoke.py"),
    Path("tests/test_block9_learning_feedback_safety_contract_audit_smoke.py"),
    Path("tests/test_block9_learning_feedback_registry_audit_smoke.py"),
    Path("tests/test_block9_learning_feedback_job_fields_audit_smoke.py"),
    Path("tests/test_block9_learning_feedback_final_audit_smoke.py"),
]

BLOCK9_STAGE_TOKENS = [
    "feedback_intake",
    "style_dna_feedback_update",
    "style_dna_review_gate",
    "style_dna_apply_plan",
    "style_dna_persistence_gate",
    "learning_pattern_recognition",
]

SAFETY_TOKENS = [
    "no_style_dna_file_write",
    "no_profile_change",
    "no_cutting_rule_activation",
    "no_timeline_modify",
    "no_render_trigger",
    "no_publish",
    "can_write_style_dna",
    "can_update_profile",
    "can_change_cutting_rules",
    "can_modify_timeline",
    "can_trigger_render",
    "can_publish",
]

FORBIDDEN_2B65_PRODUCT_FILES = [
    Path("core/block9_learning_feedback_final_audit.py"),
    Path("core/block9_learning_feedback_final_audit_runner.py"),
    Path("core/block9_learning_feedback_final_audit_signal_adapter.py"),
    Path("models/block9_learning_feedback_final_audit.py"),
]


def test_2b65_is_test_only_and_adds_no_product_runner():
    unexpected = [str(path) for path in FORBIDDEN_2B65_PRODUCT_FILES if path.exists()]
    assert unexpected == []


def test_2b65_audit_suite_files_exist():
    missing = [str(path) for path in AUDIT_TEST_FILES if not path.exists()]
    assert missing == []


def test_2b65_audit_suite_mentions_all_block9_stages():
    combined_text = "\n".join(path.read_text(encoding="utf-8-sig") for path in AUDIT_TEST_FILES)

    missing = [token for token in BLOCK9_STAGE_TOKENS if token not in combined_text]
    assert missing == []


def test_2b65_audit_suite_mentions_core_safety_contracts():
    combined_text = "\n".join(path.read_text(encoding="utf-8-sig") for path in AUDIT_TEST_FILES)

    missing = [token for token in SAFETY_TOKENS if token not in combined_text]
    assert missing == []


def test_2b65_audit_suite_does_not_request_runtime_media_work():
    import ast

    banned_import_roots = {"subprocess", "moviepy", "cv2"}
    banned_call_names = {
        "VideoFileClip",
        "AudioFileClip",
        "VideoCapture",
        "VideoWriter",
        "write_videofile",
        "system",
        "run",
        "Popen",
    }

    problems = []

    for path in AUDIT_TEST_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in banned_import_roots:
                        problems.append(f"{path}: banned import {alias.name}")

            if isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in banned_import_roots:
                    problems.append(f"{path}: banned import from {node.module}")

            if isinstance(node, ast.Call):
                func = node.func
                call_name = ""
                dotted = ""

                if isinstance(func, ast.Name):
                    call_name = func.id
                    dotted = call_name
                elif isinstance(func, ast.Attribute):
                    call_name = func.attr
                    parts = []
                    cursor = func
                    while isinstance(cursor, ast.Attribute):
                        parts.append(cursor.attr)
                        cursor = cursor.value
                    if isinstance(cursor, ast.Name):
                        parts.append(cursor.id)
                    dotted = ".".join(reversed(parts))

                if call_name in banned_call_names and (
                    dotted.startswith("subprocess.")
                    or dotted.startswith("os.")
                    or dotted.startswith("cv2.")
                    or dotted in {"VideoFileClip", "AudioFileClip", "write_videofile"}
                ):
                    problems.append(f"{path}: banned runtime call {dotted}")

    assert problems == []
