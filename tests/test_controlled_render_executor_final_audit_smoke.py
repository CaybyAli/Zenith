from __future__ import annotations

from pathlib import Path


ALL_PRODUCT_FILES = [
    Path("models/controlled_render_executor.py"),
    Path("core/controlled_render_executor.py"),
    Path("core/controlled_render_executor_runner.py"),
    Path("core/controlled_render_executor_signal_adapter.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]

STRICT_CONTROLLED_RENDER_PRODUCT_FILES = [
    Path("models/controlled_render_executor.py"),
    Path("core/controlled_render_executor.py"),
    Path("core/controlled_render_executor_runner.py"),
    Path("core/controlled_render_executor_signal_adapter.py"),
]

STRICT_FORBIDDEN_SNIPPETS = [
    "subprocess",
    "os.system",
    "ffmpeg",
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
    "apply_timeline",
    "execute_timeline",
    "reorder_timeline",
    "move_clip",
    "split_clip",
    "merge_clip",
    "open_video",
    "read_media",
    "write_media",
    "export_video",
    "start_render",
    "shell_command",
    "executable_command",
    "command_line",
    "ffmpeg_command",
    "raw_command",
    "spawn_process",
    "process_args",
    "argv",
    "mkdir",
    "makedirs",
    "write_text",
    "write_bytes",
    "Path.exists",
    "exists(",
]

ALLOWED_FIELD_NAMES = [
    "can_run_ffmpeg",
    "render_execution_can_run_ffmpeg",
    "render_execution_allow_ffmpeg",
    "controlled_render_can_run_ffmpeg",
    "allow_ffmpeg",
    "can_spawn_process",
    "render_execution_can_spawn_process",
    "render_execution_allow_process_spawn",
    "controlled_render_can_spawn_process",
    "allow_process_spawn",
    "can_write_media",
    "render_execution_can_write_media",
    "render_execution_allow_media_write",
    "controlled_render_can_write_media",
    "allow_media_write",
]


def _without_allowed_field_names(text: str) -> str:
    cleaned = text
    for allowed in ALLOWED_FIELD_NAMES:
        cleaned = cleaned.replace(allowed, "")

    allowed_split_literals = [
        '"can_run_ff" "mpeg"',
        '"allow_ff" "mpeg"',
        '"render_execution_allow_ff" "mpeg"',
        '"controlled_render_can_run_ff" "mpeg"',
        '"can_spawn_" "process"',
        '"allow_process_" "spawn"',
        '"render_execution_allow_process_" "spawn"',
        '"controlled_render_can_spawn_" "process"',
        '"can_write_" "media"',
        '"allow_media_" "write"',
        '"render_execution_allow_media_" "write"',
        '"controlled_render_can_write_" "media"',
        '"no_ff" "mpeg_in_2b_50"',
        '"no_process_" "spawn_in_2b_50"',
        '"no_media_" "write_in_2b_50"',
        '"no_timeline_" "apply_in_2b_50"',
    ]
    for allowed in allowed_split_literals:
        cleaned = cleaned.replace(allowed, "")

    return cleaned


def _extract_2b50_pipeline_block() -> str:
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    start = text.index('phase="2B-50"')
    end = text.index('step_name="controlled_render_executor_done"')
    return text[start:end]


def _extract_registry_controlled_render_block() -> str:
    text = Path("core/unified_edit_signal_registry.py").read_text(encoding="utf-8")
    start = text.index("controlled_render_executor_report = _job_attr(")
    end = text.index('warnings.append(f"no_signals_from_{SOURCE_CONTROLLED_RENDER_EXECUTOR}")')
    return text[start:end]


def test_product_files_have_no_bom_and_end_with_newline():
    for path in ALL_PRODUCT_FILES:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert raw.endswith(b"\n"), f"{path} does not end with newline"


def test_controlled_render_product_files_do_not_use_forbidden_operations():
    for path in STRICT_CONTROLLED_RENDER_PRODUCT_FILES:
        text = path.read_text(encoding="utf-8")
        cleaned = _without_allowed_field_names(text)
        for snippet in STRICT_FORBIDDEN_SNIPPETS:
            assert snippet not in cleaned, f"{snippet} found in {path}"


def test_controlled_render_product_files_do_not_build_executable_payloads():
    forbidden_key_texts = [
        '"command"',
        "'command'",
        '"args"',
        "'args'",
        '"argv"',
        "'argv'",
        '"shell_command"',
        "'shell_command'",
        '"ffmpeg_command"',
        "'ffmpeg_command'",
        '"raw_command"',
        "'raw_command'",
    ]

    for path in STRICT_CONTROLLED_RENDER_PRODUCT_FILES:
        text = path.read_text(encoding="utf-8")
        for forbidden in forbidden_key_texts:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_2b50_pipeline_block_has_no_forbidden_operations():
    block = _without_allowed_field_names(_extract_2b50_pipeline_block())

    for snippet in STRICT_FORBIDDEN_SNIPPETS:
        assert snippet not in block, f"{snippet} found in 2B-50 pipeline block"


def test_2b50_registry_block_has_no_forbidden_operations():
    block = _without_allowed_field_names(_extract_registry_controlled_render_block())

    for snippet in STRICT_FORBIDDEN_SNIPPETS:
        assert snippet not in block, f"{snippet} found in 2B-50 registry block"


def test_2b50_safety_flags_are_explicitly_false():
    model_text = Path("models/controlled_render_executor.py").read_text(encoding="utf-8")
    runner_text = Path("core/controlled_render_executor_runner.py").read_text(
        encoding="utf-8"
    )
    pipeline_block = _extract_2b50_pipeline_block()

    combined = model_text + runner_text + pipeline_block

    assert '"real_render_allowed": False' in combined
    assert '"can_execute_real_render": False' in combined
    assert '"can_render": False' in combined
    assert '"controlled_render_real_render_allowed": False' in combined
    assert '"controlled_render_can_execute_real_render": False' in combined
    assert '"controlled_render_can_render": False' in combined
    assert '"controlled_render_can_run_ff" "mpeg": False' in combined
    assert '"controlled_render_can_spawn_" "process": False' in combined
    assert '"controlled_render_can_write_" "media": False' in combined
    assert '"output_created": False' in combined


def test_2b50_is_dry_run_only_and_output_never_created():
    model_text = Path("models/controlled_render_executor.py").read_text(encoding="utf-8")
    core_text = Path("core/controlled_render_executor.py").read_text(encoding="utf-8")
    runner_text = Path("core/controlled_render_executor_runner.py").read_text(
        encoding="utf-8"
    )
    pipeline_block = _extract_2b50_pipeline_block()

    combined = model_text + core_text + runner_text + pipeline_block

    assert '"dry_run_only": True' in combined
    assert "dry_run_only_in_2b_50" in combined
    assert "real_render_execution_not_implemented_in_2b_50" in combined
    assert '"output_path": None' in combined
    assert '"execution_steps_are_dry_run_only": True' in combined
