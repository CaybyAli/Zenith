from __future__ import annotations

from pathlib import Path


PRODUCT_FILES = [
    Path("models/style_dna_apply_plan.py"),
    Path("core/style_dna_apply_plan_builder.py"),
    Path("core/style_dna_apply_plan_runner.py"),
    Path("core/style_dna_apply_plan_signal_adapter.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]

NEW_2B62_FILES = [
    Path("models/style_dna_apply_plan.py"),
    Path("core/style_dna_apply_plan_builder.py"),
    Path("core/style_dna_apply_plan_runner.py"),
    Path("core/style_dna_apply_plan_signal_adapter.py"),
]

STRICT_FORBIDDEN_IN_NEW_FILES = [
    "subprocess",
    "os.system",
    "shell=True",
    "subprocess.run",
    "subprocess.Popen",
    "execute_final_cutlist",
    "apply_final_cutlist",
    "TimelineBuilder",
    "HighlightSelector",
    "RenderProcessor",
    "moviepy",
    "cv2.VideoWriter",
    "write_videofile",
    "apply_timeline",
    "execute_timeline",
    "reorder_timeline",
    "move_clip",
    "split_clip",
    "merge_clip",
    "style_dna.write",
    "write_style_dna(",
    "save_style_dna(",
    "update_style_dna_file(",
    "profile.write",
    "update_profile(",
    "change_profile(",
    "publish_video(",
    "upload_video(",
    "autopublish(",
    "start_render(",
    "trigger_render(",
    "write_text(",
    "write_bytes(",
    "mkdir(",
    "makedirs(",
]

STRICT_FORBIDDEN_IN_NEW_FILES_PIECES = [
    ("ff", "mpeg"),
    ("ff", "probe"),
]

FORBIDDEN_ACTIONS_IN_2B62_PATCHED_BLOCKS = [
    "subprocess",
    "os.system",
    "shell=True",
    "execute_final_cutlist",
    "apply_final_cutlist",
    "TimelineBuilder",
    "HighlightSelector",
    "RenderProcessor",
    "moviepy",
    "cv2.VideoWriter",
    "write_videofile",
    "apply_timeline",
    "execute_timeline",
    "reorder_timeline",
    "move_clip",
    "split_clip",
    "merge_clip",
    "style_dna.write",
    "write_style_dna(",
    "save_style_dna(",
    "update_style_dna_file(",
    "profile.write",
    "update_profile(",
    "change_profile(",
    "publish_video(",
    "upload_video(",
    "autopublish(",
    "start_render(",
    "trigger_render(",
    "write_text(",
    "write_bytes(",
    "mkdir(",
    "makedirs(",
]


def test_product_files_exist():
    for path in PRODUCT_FILES:
        assert path.exists(), f"missing {path}"


def test_new_product_files_have_no_strict_forbidden_runtime_actions():
    for path in NEW_2B62_FILES:
        text = path.read_text(encoding="utf-8")
        for token in STRICT_FORBIDDEN_IN_NEW_FILES:
            assert token not in text, f"{token} found in {path}"
        for left, right in STRICT_FORBIDDEN_IN_NEW_FILES_PIECES:
            assert left + right not in text.lower(), f"{left + right} found in {path}"


def test_pipeline_2b62_block_has_no_dangerous_calls():
    pipeline_text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    start = pipeline_text.index('phase="2B-62"')
    end = pipeline_text.index("persist_job_state_checkpoint(", start)
    pipeline_2b62_block = pipeline_text[start:end]

    for token in FORBIDDEN_ACTIONS_IN_2B62_PATCHED_BLOCKS:
        assert token not in pipeline_2b62_block, f"{token} found in 2B-62 pipeline block"


def test_apply_plan_safety_metadata_is_present():
    combined_text = "\n".join(path.read_text(encoding="utf-8") for path in NEW_2B62_FILES)

    assert "style_dna_apply_plan_only" in combined_text
    assert "non_writing_apply_contract" in combined_text
    assert "style_dna_preview_only" in combined_text
    assert "no_style_dna_file_write_in_2b_62" in combined_text
    assert "no_profile_change_in_2b_62" in combined_text
    assert "no_cutting_rule_activation_in_2b_62" in combined_text
    assert "no_timeline_modify_in_2b_62" in combined_text
    assert "no_render_trigger_in_2b_62" in combined_text
    assert "no_publish_in_2b_62" in combined_text


def test_product_files_have_no_bom_and_end_with_newline():
    for path in PRODUCT_FILES:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"missing final newline in {path}"
