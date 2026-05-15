from __future__ import annotations

from pathlib import Path


PRODUCT_FILES = [
    "models/style_dna_feedback_update.py",
    "core/style_dna_feedback_updater.py",
    "core/style_dna_feedback_updater_runner.py",
    "core/style_dna_feedback_updater_signal_adapter.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
    "models/job.py",
]


STRICT_PRODUCT_FILES = [
    "models/style_dna_feedback_update.py",
    "core/style_dna_feedback_updater.py",
    "core/style_dna_feedback_updater_runner.py",
    "core/style_dna_feedback_updater_signal_adapter.py",
]


FORBIDDEN_IN_STRICT_PRODUCT_FILES = [
    "subprocess",
    "os.system",
    "shell=True",
    "ffmpeg",
    "ffprobe",
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
    "save_style_dna",
    "update_style_dna_file",
    "profile.write",
    "publish_video",
    "upload_video",
    "autopublish",
    "start_render",
    "write_text",
    "write_bytes",
    "mkdir",
    "makedirs",
]


FORBIDDEN_IN_2B60_PIPELINE_SNIPPET = [
    "style_dna.write",
    "save_style_dna",
    "update_style_dna_file",
    "profile.write",
    "update_profile(",
    "change_profile(",
    "publish_video",
    "upload_video",
    "autopublish",
    "start_render",
    "write_text",
    "write_bytes",
    "mkdir",
    "makedirs",
]


def test_product_files_have_no_bom_and_end_with_newline():
    for file_name in PRODUCT_FILES:
        data = Path(file_name).read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), file_name
        assert data.endswith(b"\n"), file_name


def test_new_product_files_do_not_contain_forbidden_runtime_actions():
    for file_name in STRICT_PRODUCT_FILES:
        text = Path(file_name).read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_IN_STRICT_PRODUCT_FILES:
            assert forbidden not in text, f"{forbidden} found in {file_name}"


def test_pipeline_2b60_block_does_not_contain_forbidden_actions():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    start = text.index('phase="2B-60"')
    end = text.index("persist_job_state_checkpoint", start)
    snippet = text[start:end]

    for forbidden in FORBIDDEN_IN_2B60_PIPELINE_SNIPPET:
        assert forbidden not in snippet, f"{forbidden} found in 2B-60 pipeline snippet"


def test_registry_2b60_block_does_not_contain_forbidden_actions():
    text = Path("core/unified_edit_signal_registry.py").read_text(encoding="utf-8")
    start = text.index("style_dna_feedback_update_report")
    end = text.index("if final_cut_list_signals:", start)
    snippet = text[start:end]

    for forbidden in FORBIDDEN_IN_2B60_PIPELINE_SNIPPET:
        assert forbidden not in snippet, f"{forbidden} found in 2B-60 registry snippet"


def test_job_fields_force_dangerous_permissions_false():
    text = Path("models/job.py").read_text(encoding="utf-8")

    assert "style_dna_update_can_write_style_dna=False" in text
    assert "style_dna_update_can_update_profile=False" in text
    assert "style_dna_update_can_change_cutting_rules=False" in text
    assert "style_dna_update_can_modify_timeline=False" in text
    assert "style_dna_update_can_trigger_render=False" in text
    assert "style_dna_update_can_publish=False" in text


def test_required_safety_permission_fields_are_allowed():
    for file_name in PRODUCT_FILES:
        text = Path(file_name).read_text(encoding="utf-8")
        if "style_dna_update_can_write_style_dna" in text:
            assert "style_dna_update_can_write_style_dna" in text
        if "style_dna_update_can_trigger_render" in text:
            assert "style_dna_update_can_trigger_render" in text
        if "can_write_style_dna" in text:
            assert "can_write_style_dna" in text
        if "can_trigger_render" in text:
            assert "can_trigger_render" in text
