from __future__ import annotations

from pathlib import Path


NEW_PRODUCT_FILES = [
    Path("models/render_verification_contract.py"),
    Path("core/render_verification_contract.py"),
    Path("core/render_verification_contract_runner.py"),
    Path("core/render_verification_contract_signal_adapter.py"),
]

MODIFIED_PRODUCT_FILES = [
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]

PRODUCT_FILES = NEW_PRODUCT_FILES + MODIFIED_PRODUCT_FILES

STRICT_FORBIDDEN_TOKENS = [
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
    "open_video",
    "read_media(",
    "write_media(",
    "full_render(",
    "render_timeline(",
    "user_media_input(",
    "start_render(",
    "export_video(",
    "mkdir(",
    "makedirs(",
    "write_text(",
    "write_bytes(",
]

ALLOWED_PROJECT_OUTPUT_CONTEXTS = [
    "output_can_write_project_output",
    "controlled_ffmpeg_can_write_project_output",
    "controlled_ffmpeg_can_write_project_output=False",
    "controlled_ffmpeg_can_write_project_output = False",
    "render_verification_project_output_probe_allowed",
    "render_verification_can_verify_project_output",
    "render_verification_allow_project_output_probe",
    "can_write_project_output",
    "can_probe_project_output",
    "render_verification_project_output_still_not_allowed",
    "project_output_still_not_allowed",
    "project_output_probe_allowed",
    "can_verify_project_output",
    "no_project_",
    "project_\" \"output",
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_render_verification_product_files_exist():
    for path in PRODUCT_FILES:
        assert path.exists(), f"missing product file: {path}"


def test_render_verification_product_files_have_no_bom_and_end_with_newline():
    for path in PRODUCT_FILES:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"BOM found: {path}"
        assert data.endswith(b"\n"), f"missing trailing newline: {path}"


def test_render_verification_new_product_files_do_not_use_strict_forbidden_media_operations():
    for path in NEW_PRODUCT_FILES:
        text = _text(path)
        for token in STRICT_FORBIDDEN_TOKENS:
            assert token not in text, f"{token} found in {path}"


def test_render_verification_modified_files_do_not_use_forbidden_tokens_in_2b_56_lines():
    for path in MODIFIED_PRODUCT_FILES:
        for line_no, line in enumerate(_text(path).splitlines(), start=1):
            if "2B-56" not in line and "render_verification" not in line:
                continue
            for token in STRICT_FORBIDDEN_TOKENS:
                assert token not in line, f"{token} found in {path}:{line_no}: {line}"


def test_render_verification_does_not_contain_unapproved_project_output_usage():
    for path in PRODUCT_FILES:
        for line_no, line in enumerate(_text(path).splitlines(), start=1):
            if "project_output" not in line:
                continue
            if any(allowed in line for allowed in ALLOWED_PROJECT_OUTPUT_CONTEXTS):
                continue
            raise AssertionError(f"unapproved project_output usage in {path}:{line_no}: {line}")


def test_render_verification_core_does_not_execute_ffprobe_or_ffmpeg():
    core_text = _text(Path("core/render_verification_contract.py"))
    runner_text = _text(Path("core/render_verification_contract_runner.py"))

    forbidden_runtime_calls = [
        "subprocess.run(",
        "subprocess.Popen(",
        "check_output(",
        "os.system(",
        "startfile(",
        "shell=True",
    ]

    for token in forbidden_runtime_calls:
        assert token not in core_text
        assert token not in runner_text

    assert "argv_preview" in core_text
    assert "<OUTPUT_PATH_PLACEHOLDER>" in core_text
    assert "can_execute_probe=False" in core_text
    assert "can_probe_media_files=False" in core_text
    assert "can_render=False" in core_text
    assert "can_write_media=False" in core_text


def test_render_verification_final_audit_safety_metadata_present():
    required_metadata_tokens = [
        '"phase": "2B-56"',
        '"block": "block8_render_export"',
        '"render_verification_contract_only": True',
        '"dry_run_only": True',
        '"probe_plan_only": True',
        '"no_" "full_" "render_in_2b_56": True',
        '"no_" "ff" "probe_execution_in_2b_56": True',
        '"no_project_" "output_probe_in_2b_56": True',
        '"no_user_media_" "input_in_2b_56": True',
        '"no_project_" "output_write_in_2b_56": True',
        '"no_timeline_" "apply_in_2b_56": True',
    ]

    combined = "\n".join(_text(path) for path in PRODUCT_FILES)
    for token in required_metadata_tokens:
        assert token in combined
