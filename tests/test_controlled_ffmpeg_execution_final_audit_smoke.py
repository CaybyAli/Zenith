from __future__ import annotations

from pathlib import Path


PRODUCT_FILES = [
    Path("models/controlled_ffmpeg_execution.py"),
    Path("core/controlled_ffmpeg_execution.py"),
    Path("core/controlled_ffmpeg_execution_runner.py"),
    Path("core/controlled_ffmpeg_execution_signal_adapter.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_product_files_have_no_bom_and_end_with_newline():
    for path in PRODUCT_FILES:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"


def test_subprocess_run_only_allowed_in_controlled_ffmpeg_execution_core():
    for path in PRODUCT_FILES:
        text = _text(path)
        if path.as_posix() == "core/controlled_ffmpeg_execution.py":
            assert "subprocess.run(" in text
        else:
            assert "subprocess.run(" not in text


def test_no_forbidden_execution_patterns():
    forbidden = [
        "os.system",
        "shell=True",
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
        "read_media",
        "write_media",
    ]

    allowed_safety_terms = {
        "full_render",
        "render_timeline",
        "project_output",
        "user_media_input",
        "no_project_output",
        "no_user_media_input",
        "no_full_render_in_2b_54",
        "no_project_output_in_2b_54",
        "no_user_media_input_in_2b_54",
        "can_execute_full_render",
        "can_render_timeline",
        "can_write_project_output",
        "can_process_user_media",
        "can_write_media",
        "ffmpeg_can_write_media",
        "ffmpeg_command_can_write_media",
        "controlled_render_can_write_media",
        "controlled_ffmpeg_can_write_project_output",
        "controlled_ffmpeg_can_process_user_media",
        "controlled_ffmpeg_can_render_timeline",
        "controlled_ffmpeg_can_execute_full_render",
        "ffmpeg_write_media_permission_must_remain_false_before_2b54",
        "ffmpeg_command_write_media_permission_must_remain_false_before_2b54",
        "smoke_test_succeeded_no_full_render_unlocked",
        "does_not_unlock_full_render",
        "controlled_ffmpeg_full_render_still_not_allowed",
        "controlled_ffmpeg_user_media_still_not_allowed",
        "controlled_ffmpeg_project_output_still_not_allowed",
    }

    strict_new_files = [
        Path("models/controlled_ffmpeg_execution.py"),
        Path("core/controlled_ffmpeg_execution.py"),
        Path("core/controlled_ffmpeg_execution_runner.py"),
        Path("core/controlled_ffmpeg_execution_signal_adapter.py"),
    ]

    for path in strict_new_files:
        scan_text = _text(path)
        for term in allowed_safety_terms:
            scan_text = scan_text.replace(term, "")

        for term in forbidden:
            assert term not in scan_text, f"{term} found in {path}"

    pipeline_text = _text(Path("core/gaming_pipeline.py"))
    start = pipeline_text.index('"CONTROLLED_FF" "MPEG_EXECUTION_STARTED"')
    end = pipeline_text.index('"controlled_" "ff" "mpeg_execution_done"') + 1000
    pipeline_2b54_area = pipeline_text[start:end]

    registry_text = _text(Path("core/unified_edit_signal_registry.py"))
    start = registry_text.index("controlled_ff_exec_report = _job_attr")
    end = registry_text.index("if final_cut_list_signals:")
    registry_2b54_area = registry_text[start:end]

    job_text = _text(Path("models/job.py"))
    start = job_text.index("ffmpeg_execution_requested_mode")
    end = job_text.index("silence_classification_report", start)
    job_2b54_area = job_text[start:end]

    for label, scan_text in {
        "core/gaming_pipeline.py 2B-54 area": pipeline_2b54_area,
        "core/unified_edit_signal_registry.py 2B-54 area": registry_2b54_area,
        "models/job.py 2B-54 area": job_2b54_area,
    }.items():
        for term in allowed_safety_terms:
            scan_text = scan_text.replace(term, "")

        for term in forbidden:
            assert term not in scan_text, f"{term} found in {label}"


def test_controlled_ffmpeg_execution_core_has_required_safety_tokens():
    text = _text(Path("core/controlled_ffmpeg_execution.py"))

    assert "subprocess.run(" in text
    assert "shell=False" in text
    assert "timeout=timeout_seconds" in text
    assert "capture_output=True" in text
    assert "check=False" in text
    assert "lavfi" in text
    assert "testsrc=size=320x180:rate=10" in text
    assert "sine=frequency=1000" in text
    assert "tempfile.gettempdir()" in text
    assert "MAX_SMOKE_DURATION_SECONDS = 2.0" in text


def test_full_render_timeline_user_media_and_project_output_remain_locked():
    model_text = _text(Path("models/controlled_ffmpeg_execution.py"))
    core_text = _text(Path("core/controlled_ffmpeg_execution.py"))
    job_text = _text(Path("models/job.py"))

    combined = "\n".join([model_text, core_text, job_text])

    assert "can_execute_full_render=False" in combined or "can_execute_full_render = False" in combined
    assert "can_render_timeline=False" in combined or "can_render_timeline = False" in combined
    assert "can_process_user_media=False" in combined or "can_process_user_media = False" in combined
    assert "can_write_project_output=False" in combined or "can_write_project_output = False" in combined
    assert "controlled_ffmpeg_can_execute_full_render=False" in combined
    assert "controlled_ffmpeg_can_render_timeline=False" in combined
    assert "controlled_ffmpeg_can_process_user_media=False" in combined
    assert "controlled_ffmpeg_can_write_project_output=False" in combined


def test_command_is_internal_lavfi_only_not_job_user_argv():
    text = _text(Path("core/controlled_ffmpeg_execution.py"))

    assert "_build_internal_smoke_command" in text
    assert "ffmpeg_command_assemblies" not in text
    assert "raw_video_path" not in text
    assert "argument_tokens" not in text
    assert "argv_preview" not in text
