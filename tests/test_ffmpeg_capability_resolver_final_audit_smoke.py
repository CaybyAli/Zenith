from __future__ import annotations

from pathlib import Path


PRODUCT_FILES = [
    Path("models/ffmpeg_capability_resolver.py"),
    Path("core/ffmpeg_capability_resolver.py"),
    Path("core/ffmpeg_capability_resolver_runner.py"),
    Path("core/ffmpeg_capability_resolver_signal_adapter.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]

FFMPEG_PRODUCT_FILES = [
    Path("models/ffmpeg_capability_resolver.py"),
    Path("core/ffmpeg_capability_resolver.py"),
    Path("core/ffmpeg_capability_resolver_runner.py"),
    Path("core/ffmpeg_capability_resolver_signal_adapter.py"),
]

FORBIDDEN_ALWAYS = [
    "os.system",
    "shell=True",
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
    "write_media(",
    "export_video",
    "start_render",
    "shell_command",
    "executable_command",
    "command_line",
    "raw_command",
    "mkdir",
    "makedirs",
    "write_text",
    "write_bytes",
]

FORBIDDEN_PROBE_ARGS = [
    '"-i"',
    "'-i'",
    '"-y"',
    "'-y'",
    "filter_complex",
    "media_path",
]

ALLOWED_PROBES = [
    '"-version"',
    '"-encoders"',
    '"-decoders"',
    '"-filters"',
    '"-hwaccels"',
]


def test_product_files_have_no_bom_and_end_with_newline() -> None:
    for path in PRODUCT_FILES:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), path
        assert data.endswith(b"\n"), path


def test_final_audit_allows_only_controlled_tool_probes() -> None:
    resolver_text = Path("core/ffmpeg_capability_resolver.py").read_text(
        encoding="utf-8"
    )

    assert "subprocess.run" in resolver_text
    assert "shell=False" in resolver_text
    assert "timeout=10" in resolver_text
    assert "capture_output=True" in resolver_text
    assert "text=True" in resolver_text

    for probe in ALLOWED_PROBES:
        assert probe in resolver_text

    for bad in FORBIDDEN_PROBE_ARGS:
        assert bad not in resolver_text


def test_final_audit_forbids_render_media_input_media_output_and_shell_escape() -> None:
    for path in FFMPEG_PRODUCT_FILES:
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_ALWAYS:
            assert forbidden not in text, f"{forbidden} found in {path}"

    for path in PRODUCT_FILES:
        text = path.read_text(encoding="utf-8")
        assert "shell=True" not in text, path
        assert "os.system" not in text, path


def test_subprocess_run_only_exists_in_core_resolver() -> None:
    for path in PRODUCT_FILES:
        text = path.read_text(encoding="utf-8")
        if path.as_posix() == "core/ffmpeg_capability_resolver.py":
            assert "subprocess.run" in text
        else:
            assert "subprocess.run" not in text
