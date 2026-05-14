from __future__ import annotations

import ast
from pathlib import Path


BLOCK7_PRODUCT_FILES = [
    "models/hook_identification.py",
    "core/hook_identification_engine.py",
    "core/hook_identification_runner.py",
    "core/hook_identification_signal_adapter.py",
    "models/emotional_arc.py",
    "core/emotional_arc_builder.py",
    "core/emotional_arc_runner.py",
    "core/emotional_arc_signal_adapter.py",
    "models/dynamic_pacing.py",
    "core/dynamic_pacing_engine.py",
    "core/dynamic_pacing_runner.py",
    "core/dynamic_pacing_signal_adapter.py",
    "models/pattern_interrupt.py",
    "core/pattern_interrupt_engine.py",
    "core/pattern_interrupt_runner.py",
    "core/pattern_interrupt_signal_adapter.py",
    "models/reaction_shot_placement.py",
    "core/reaction_shot_placement_engine.py",
    "core/reaction_shot_placement_runner.py",
    "core/reaction_shot_placement_signal_adapter.py",
    "models/but_therefore_story.py",
    "core/but_therefore_story_engine.py",
    "core/but_therefore_story_runner.py",
    "core/but_therefore_story_signal_adapter.py",
    "models/final_quality_validator.py",
    "core/final_quality_validator.py",
    "core/final_quality_validator_runner.py",
    "core/final_quality_validator_signal_adapter.py",
]

CENTRAL_FILES = [
    "models/job.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
]

FORBIDDEN_IMPORTS = {
    "subprocess",
    "moviepy",
    "cv2",
}

FORBIDDEN_CALL_NAMES = {
    "system",
    "render_video",
    "execute_final_cutlist",
    "apply_final_cutlist",
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
    "apply_hook",
    "apply_arc",
    "apply_pacing",
    "apply_pattern",
    "apply_reaction",
    "apply_story",
    "apply_quality_fix",
    "execute_quality_fix",
    "auto_fix",
    "auto_correct",
    "auto_remove",
    "auto_trim",
    "insert_zoom",
    "apply_zoom",
    "insert_text_overlay",
    "apply_text_overlay",
    "insert_sfx",
    "apply_sfx",
    "add_overlay",
    "add_effect",
    "move_facecam",
    "insert_reaction",
    "place_reaction",
    "remove_and_moment",
    "remove_and_moments",
}

FORBIDDEN_TEXT_PATTERNS = [
    "ffmpeg",
    "TimelineBuilder",
    "HighlightSelector",
    "cv2.VideoWriter",
]

HARD_MEDIA_PATH_PATTERNS = [
    "D:\\",
    "C:\\",
    "/mnt/",
    "/home/",
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".wav",
    ".mp3",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def test_all_block7_product_and_central_files_exist():
    missing = [
        rel
        for rel in [*BLOCK7_PRODUCT_FILES, *CENTRAL_FILES]
        if not Path(rel).is_file()
    ]

    assert missing == []


def test_block7_product_files_have_no_bom_and_end_with_newline():
    bad_bom = []
    bad_newline = []

    for rel in BLOCK7_PRODUCT_FILES:
        raw = Path(rel).read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            bad_bom.append(rel)
        if raw and not raw.endswith(b"\n"):
            bad_newline.append(rel)

    assert bad_bom == []
    assert bad_newline == []


BLOCK7_CONTRACT_OWNER_FILES = [
    "core/hook_identification_runner.py",
    "core/emotional_arc_runner.py",
    "core/dynamic_pacing_runner.py",
    "core/pattern_interrupt_runner.py",
    "core/reaction_shot_placement_runner.py",
    "core/but_therefore_story_runner.py",
    "core/final_quality_validator.py",
]


def test_block7_product_files_expose_review_only_safety_contract():
    missing_review_only_safety = {}

    for rel in BLOCK7_PRODUCT_FILES:
        text = _read_text(Path(rel))
        safety_markers = [
            "review_only",
            "enforce_review_only",
            "can_render",
            "can_apply",
            "media_unchanged",
        ]
        if not any(marker in text for marker in safety_markers):
            missing_review_only_safety[rel] = safety_markers

    assert missing_review_only_safety == {}


def test_block7_contract_owner_files_have_block_metadata_and_media_unchanged():
    missing_contract = {}

    for rel in BLOCK7_CONTRACT_OWNER_FILES:
        text = _read_text(Path(rel))
        missing = []
        for marker in [
            "block7_story_pacing",
            "review_only",
            "media_unchanged",
        ]:
            if marker not in text:
                missing.append(marker)

        if missing:
            missing_contract[rel] = missing

    assert missing_contract == {}


def test_block7_product_files_do_not_import_real_media_execution_libraries():
    violations = []

    for rel in BLOCK7_PRODUCT_FILES:
        tree = ast.parse(_read_text(Path(rel)), filename=rel)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".")[0]
                    if root_name in FORBIDDEN_IMPORTS:
                        violations.append((rel, node.lineno, alias.name))

            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                root_name = module.split(".")[0]
                if root_name in FORBIDDEN_IMPORTS:
                    violations.append((rel, node.lineno, module))

    assert violations == []


def test_block7_product_files_do_not_call_real_media_or_timeline_execution():
    violations = []

    for rel in BLOCK7_PRODUCT_FILES:
        tree = ast.parse(_read_text(Path(rel)), filename=rel)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            call_name = _call_name(node.func)
            if call_name in FORBIDDEN_CALL_NAMES:
                violations.append((rel, node.lineno, call_name))

            if isinstance(node.func, ast.Attribute):
                owner = _call_name(node.func.value)
                dotted = f"{owner}.{node.func.attr}" if owner else node.func.attr
                if dotted in {"os.system", "cv2.VideoWriter"}:
                    violations.append((rel, node.lineno, dotted))

    assert violations == []


def test_block7_product_files_do_not_reference_render_or_media_paths():
    violations = []

    for rel in BLOCK7_PRODUCT_FILES:
        text = _read_text(Path(rel))

        for pattern in FORBIDDEN_TEXT_PATTERNS:
            if pattern in text:
                violations.append((rel, pattern))

        for pattern in HARD_MEDIA_PATH_PATTERNS:
            if pattern in text:
                violations.append((rel, pattern))

    assert violations == []


def test_block7_product_files_never_set_execution_permissions_true():
    dangerous_true_assignments = {
        "can_render",
        "can_apply",
        "can_reorder_timeline",
        "can_split_clips",
        "can_merge_clips",
        "can_trim",
        "can_extend",
        "can_insert_clip",
        "can_insert_zoom",
        "can_insert_text_overlay",
        "can_insert_sfx",
        "can_apply_changes",
        "can_remove_and_moments",
        "can_apply_fixes",
        "can_execute_timeline",
        "can_insert_effects",
    }
    violations = []

    for rel in BLOCK7_PRODUCT_FILES:
        tree = ast.parse(_read_text(Path(rel)), filename=rel)

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                is_true = isinstance(node.value, ast.Constant) and node.value.value is True
                if not is_true:
                    continue

                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in dangerous_true_assignments:
                        violations.append((rel, node.lineno, target.id))

                    if isinstance(target, ast.Attribute) and target.attr in dangerous_true_assignments:
                        violations.append((rel, node.lineno, target.attr))

            if isinstance(node, ast.keyword):
                is_true = isinstance(node.value, ast.Constant) and node.value.value is True
                if is_true and node.arg in dangerous_true_assignments:
                    violations.append((rel, getattr(node, "lineno", 0), node.arg))

    assert violations == []
