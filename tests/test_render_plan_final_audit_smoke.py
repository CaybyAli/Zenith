from pathlib import Path


PRODUCT_FILES = [
    Path("models/render_plan.py"),
    Path("core/render_plan_builder.py"),
    Path("core/render_plan_runner.py"),
    Path("core/render_plan_signal_adapter.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]

STRICT_RENDER_PLAN_FILES = [
    Path("models/render_plan.py"),
    Path("core/render_plan_builder.py"),
    Path("core/render_plan_runner.py"),
    Path("core/render_plan_signal_adapter.py"),
]


FORBIDDEN_RENDER_PLAN_TERMS = [
    "subprocess",
    "os.system",
    "ffprobe",
    "render_video",
    "execute_final_cutlist",
    "apply_final_cutlist",
    "TimelineBuilder",
    "HighlightSelector",
    "RenderProcessor",
    "moviepy",
    "cv2.VideoWriter",
    "write_videofile",
    "delete_media",
    "remove_file",
    "trim_now",
    "censor_now",
    "mute_track",
    "execute_timeline",
    "reorder_timeline",
    "move_clip",
    "split_clip",
    "merge_clip",
    "open_video",
    "read_media",
    "export_video",
    "start_render(",
    "write_media(",
    "shell_command",
    "executable_command",
    "command_line",
    "ffmpeg_command",
    "raw_command",
    '"command"',
    "'command'",
    '"argv"',
    "'argv'",
    '"args"',
    "'args'",
]


def test_render_plan_product_files_have_no_bom_and_end_with_newline():
    for path in PRODUCT_FILES:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM gefunden: {path}"
        assert raw.endswith(b"\n"), f"Keine Newline am Ende: {path}"


def test_render_plan_strict_files_have_no_forbidden_media_operations():
    for path in STRICT_RENDER_PLAN_FILES:
        text = path.read_text(encoding="utf-8")
        for term in FORBIDDEN_RENDER_PLAN_TERMS:
            assert term not in text, f"Forbidden term {term!r} in {path}"


def test_render_plan_files_keep_dry_run_safety_flags():
    text = "\n".join(path.read_text(encoding="utf-8") for path in STRICT_RENDER_PLAN_FILES)

    assert "dry_run_only" in text
    assert "ready_for_renderer_contract" in text
    assert "can_execute_plan" in text
    assert "can_render" in text
    assert "can_run_ffmpeg" in text
    assert "can_write_media" in text
    assert "can_apply_timeline" in text

    assert "can_execute_plan=False" in text or '"render_plan_can_execute_plan": False' in text
    assert "can_render=False" in text or '"render_plan_can_render": False' in text
    assert "can_run_ffmpeg=False" in text or '"render_plan_can_run_ffmpeg": False' in text
    assert "can_write_media=False" in text or '"render_plan_can_write_media": False' in text
    assert "can_apply_timeline=False" in text or '"render_plan_can_apply_timeline": False' in text


def test_render_plan_operation_intents_are_not_executable_commands():
    text = Path("core/render_plan_builder.py").read_text(encoding="utf-8")

    assert "RenderOperationIntent" in text
    assert "can_execute_now=False" in text
    assert "requires_later_renderer=True" in text
    assert "trim_intent" in text
    assert "concat_intent" in text
    assert "output_encode_intent" in text
    assert "ffmpeg_command" not in text
    assert "raw_command" not in text
    assert "shell_command" not in text
    assert "executable_command" not in text
