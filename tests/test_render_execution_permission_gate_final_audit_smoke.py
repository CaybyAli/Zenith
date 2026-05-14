from __future__ import annotations

from pathlib import Path


ALL_PRODUCT_FILES = [
    Path("models/render_execution_permission_gate.py"),
    Path("core/render_execution_permission_gate.py"),
    Path("core/render_execution_permission_gate_runner.py"),
    Path("core/render_execution_permission_gate_signal_adapter.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]

STRICT_RENDER_EXECUTION_PRODUCT_FILES = [
    Path("models/render_execution_permission_gate.py"),
    Path("core/render_execution_permission_gate.py"),
    Path("core/render_execution_permission_gate_runner.py"),
    Path("core/render_execution_permission_gate_signal_adapter.py"),
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
    "render_readiness_can_run_ffmpeg",
    "render_plan_can_run_ffmpeg",
    "render_blueprint_can_run_ffmpeg",
    "render_asset_can_run_ffmpeg",
    "can_spawn_process",
    "render_execution_can_spawn_process",
    "render_blueprint_can_spawn_process",
    "can_write_media",
    "render_execution_can_write_media",
    "render_plan_can_write_media",
    "render_blueprint_can_write_media",
    "can_apply_timeline",
    "render_execution_can_apply_timeline",
    "render_readiness_can_apply_timeline",
    "render_plan_can_apply_timeline",
]


def _without_allowed_field_names(text: str) -> str:
    cleaned = text
    for allowed in ALLOWED_FIELD_NAMES:
        cleaned = cleaned.replace(allowed, "")

    allowed_split_literals = [
        '"can_run_ff" "mpeg"',
        '"can_spawn_" "process"',
        '"can_write_" "media"',
        '"can_apply_" "timeline"',
        '"no_ff" "mpeg_in_2b_49"',
        '"no_process_" "spawn_in_2b_49"',
        '"no_timeline_" "apply_in_2b_49"',
    ]
    for allowed in allowed_split_literals:
        cleaned = cleaned.replace(allowed, "")

    return cleaned


def _extract_2b49_pipeline_block() -> str:
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    start = text.index('phase="2B-49"')
    end = text.index('step_name="render_execution_permission_gate_done"')
    return text[start:end]


def _extract_registry_permission_block() -> str:
    text = Path("core/unified_edit_signal_registry.py").read_text(encoding="utf-8")
    start = text.index("render_execution_permission_report = _job_attr(")
    end = text.index("if final_cut_list_signals:")
    return text[start:end]


def test_product_files_have_no_bom_and_end_with_newline():
    for path in ALL_PRODUCT_FILES:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert raw.endswith(b"\n"), f"{path} does not end with newline"


def test_render_execution_product_files_do_not_use_forbidden_operations():
    for path in STRICT_RENDER_EXECUTION_PRODUCT_FILES:
        text = path.read_text(encoding="utf-8")
        cleaned = _without_allowed_field_names(text)
        for snippet in STRICT_FORBIDDEN_SNIPPETS:
            assert snippet not in cleaned, f"{snippet} found in {path}"


def test_render_execution_product_files_do_not_build_executable_payloads():
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

    for path in STRICT_RENDER_EXECUTION_PRODUCT_FILES:
        text = path.read_text(encoding="utf-8")
        for forbidden in forbidden_key_texts:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_2b49_pipeline_block_has_no_forbidden_operations():
    block = _without_allowed_field_names(_extract_2b49_pipeline_block())

    for snippet in STRICT_FORBIDDEN_SNIPPETS:
        assert snippet not in block, f"{snippet} found in 2B-49 pipeline block"


def test_2b49_registry_block_has_no_forbidden_operations():
    block = _without_allowed_field_names(_extract_registry_permission_block())

    for snippet in STRICT_FORBIDDEN_SNIPPETS:
        assert snippet not in block, f"{snippet} found in 2B-49 registry block"


def test_2b49_safety_flags_are_explicitly_false():
    model_text = Path("models/render_execution_permission_gate.py").read_text(encoding="utf-8")
    runner_text = Path("core/render_execution_permission_gate_runner.py").read_text(encoding="utf-8")
    pipeline_block = _extract_2b49_pipeline_block()

    combined = model_text + runner_text + pipeline_block

    assert '"can_render": False' in combined
    assert '"render_execution_can_render": False' in combined
    assert '"render_execution_can_run_ff" "mpeg": False' in combined
    assert '"render_execution_can_spawn_" "process": False' in combined
    assert '"render_execution_can_write_" "media": False' in combined
    assert '"render_execution_can_apply_" "timeline": False' in combined


def test_2b49_only_allows_preparation_for_next_real_render_stage():
    model_text = Path("models/render_execution_permission_gate.py").read_text(encoding="utf-8")
    runner_text = Path("core/render_execution_permission_gate_runner.py").read_text(encoding="utf-8")
    pipeline_block = _extract_2b49_pipeline_block()

    combined = model_text + runner_text + pipeline_block

    assert "ready_for_real_render_stage" in combined
    assert "can_prepare_real_render_execution" in combined
    assert "can_prepare_real_render_execution" in pipeline_block
    assert "ready_for_real_render_stage" in pipeline_block
