from __future__ import annotations

from pathlib import Path


PRODUCT_FILES = [
    Path("models/feedback_intake.py"),
    Path("core/feedback_intake.py"),
    Path("core/feedback_intake_runner.py"),
    Path("core/feedback_intake_signal_adapter.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]

NEW_PRODUCT_FILES = [
    Path("models/feedback_intake.py"),
    Path("core/feedback_intake.py"),
    Path("core/feedback_intake_runner.py"),
    Path("core/feedback_intake_signal_adapter.py"),
]

STRICT_FORBIDDEN_TOKENS = [
    "subprocess",
    "os.system",
    "shell=True",
    "subprocess.run",
    "subprocess.Popen",
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
    "style_dna_update(",
    "update_style_dna(",
    "save_style_dna(",
    "profile.write",
    "update_profile(",
    "change_profile(",
    "publish_video",
    "upload_video",
    "autopublish",
    "start_render(",
    "trigger_render(",
]

ALLOWED_EXISTING_CONTEXT_TOKENS = [
    "ffmpeg",
    "ffprobe",
    "subprocess",
    "subprocess.run",
    "subprocess.Popen",
    "RenderProcessor",
    "autopublish",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_feedback_intake_final_audit_files_exist_without_bom_and_end_newline():
    for path in PRODUCT_FILES:
        assert path.exists(), f"missing product file: {path}"
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found: {path}"
        assert raw.endswith(b"\n"), f"missing final newline: {path}"


def test_feedback_intake_new_product_files_do_not_contain_forbidden_actions():
    for path in NEW_PRODUCT_FILES:
        text = _read(path)
        lowered = text.lower()
        for token in STRICT_FORBIDDEN_TOKENS:
            assert token.lower() not in lowered, f"{token} found in {path}"


def test_feedback_intake_changed_existing_files_do_not_add_forbidden_actions_near_feedback():
    for path in [
        Path("core/gaming_pipeline.py"),
        Path("core/unified_edit_signal_registry.py"),
        Path("models/job.py"),
    ]:
        text = _read(path)
        assert "feedback_intake" in text

        feedback_windows = []
        start = 0
        while True:
            idx = text.find("feedback_intake", start)
            if idx == -1:
                break
            feedback_windows.append(text[max(0, idx - 600) : idx + 1600].lower())
            start = idx + 1

        joined = "\n".join(feedback_windows)
        for token in STRICT_FORBIDDEN_TOKENS:
            if token in ALLOWED_EXISTING_CONTEXT_TOKENS:
                continue
            assert token.lower() not in joined, f"{token} found near feedback block in {path}"


def test_feedback_intake_final_audit_safety_flags_are_locked_false():
    expected_flags = [
        "can_update_style_dna",
        "can_change_profile",
        "can_change_cutting_rules",
        "can_modify_timeline",
        "can_trigger_render",
        "can_publish",
    ]

    for path in [
        Path("models/feedback_intake.py"),
        Path("core/feedback_intake.py"),
        Path("core/feedback_intake_runner.py"),
        Path("models/job.py"),
    ]:
        text = _read(path)

        for flag in expected_flags:
            assert flag in text, f"{flag} missing in {path}"

    runner_text = _read(Path("core/feedback_intake_runner.py"))
    assert '_assign(job, "feedback_can_update_style_dna", False)' in runner_text
    assert '_assign(job, "feedback_can_change_profile", False)' in runner_text
    assert '_assign(job, "feedback_can_change_cutting_rules", False)' in runner_text
    assert '_assign(job, "feedback_can_modify_timeline", False)' in runner_text
    assert '_assign(job, "feedback_can_trigger_render", False)' in runner_text
    assert '_assign(job, "feedback_can_publish", False)' in runner_text

    job_text = _read(Path("models/job.py"))
    assert "feedback_can_update_style_dna=False" in job_text
    assert "feedback_can_change_profile=False" in job_text
    assert "feedback_can_change_cutting_rules=False" in job_text
    assert "feedback_can_modify_timeline=False" in job_text
    assert "feedback_can_trigger_render=False" in job_text
    assert "feedback_can_publish=False" in job_text
