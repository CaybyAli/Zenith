from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path("scripts/k3k6_visual_proof_preview.py")


def load_tool():
    spec = importlib.util.spec_from_file_location("k3k6_visual_proof_preview", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_rejects_duration_over_5_seconds() -> None:
    tool = load_tool()
    with pytest.raises((RuntimeError, ValueError)):
        tool.validate_duration(6)


def test_rejects_output_dir_inside_repo() -> None:
    tool = load_tool()
    with pytest.raises((RuntimeError, ValueError)):
        tool.validate_output_dir(tool.repo_root() / "reports" / "bad")


def test_default_output_dir_is_temp_visual_proof_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tool = load_tool()
    monkeypatch.setenv("TEMP", str(tmp_path))
    assert tool.default_output_dir() == tmp_path / "zenith_k3k6_visual_proof_1b"


def test_no_qwen_or_ollama_imports_in_script_source() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8").casefold()
    forbidden = [
        "qwen",
        "ollama",
        "localqwen",
        "api/generate",
    ]
    for needle in forbidden:
        assert needle not in text


def test_manifest_declares_temp_only_no_ingest_no_music_no_qwen(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tool = load_tool()
    monkeypatch.setenv("TEMP", str(tmp_path))
    out_dir = tmp_path / "zenith_k3k6_visual_proof_1b"
    paths = tool.build_output_paths(out_dir)
    manifest = tool.build_manifest(
        paths,
        duration=4,
        layout_plan={
            "layout_codepath": "core.shorts_reframe_planner.ShortsReframePlanner.plan_reframe",
            "focus_or_reframe_codepath_used": True,
            "layout_type": "hybrid_split",
        },
        dry_run=True,
    )
    assert manifest["safety"]["temp_only"] is True
    assert manifest["safety"]["ingest"] is False
    assert manifest["safety"]["qwen"] is False
    assert manifest["safety"]["music"] is False
    assert manifest["safety"]["full_render"] is False


def test_duration_and_preview_command_limited(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tool = load_tool()
    monkeypatch.setattr(tool, "get_ffmpeg_path", lambda: "FFMPEG")
    command = tool.build_ffmpeg_command(
        video_path=tmp_path / "source.mp4",
        timestamp=1,
        duration=5,
        output_video=tmp_path / "out.mp4",
        ass_path=tmp_path / "captions.ass",
    )
    duration_arg = command[command.index("-t") + 1]
    assert float(duration_arg) <= 5.0

    with pytest.raises((RuntimeError, ValueError)):
        tool.build_ffmpeg_command(
            video_path=tmp_path / "source.mp4",
            timestamp=1,
            duration=5.1,
            output_video=tmp_path / "out.mp4",
            ass_path=tmp_path / "captions.ass",
        )


def test_script_uses_ffmpeg_helper_not_hardcoded_paths() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "get_ffmpeg_path" in text
    assert "get_ffprobe_path" in text
    forbidden = [
        r"D:\Tools\ffmpeg",
        r"C:\ffmpeg",
        "ffmpeg.exe",
        "ffprobe.exe",
    ]
    for needle in forbidden:
        assert needle not in text


def test_caption_and_layout_outputs_are_temp_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tool = load_tool()
    monkeypatch.setenv("TEMP", str(tmp_path))
    out_dir = tmp_path / "zenith_k3k6_visual_proof_1b"
    paths = tool.build_output_paths(out_dir)

    assert paths["caption_ass"].name == "k3_caption_proof.ass"
    assert paths["layout_json"].name == "k6_layout_proof.json"
    assert paths["manifest"].name == "visual_proof_manifest.json"

    for key in ("caption_ass", "layout_json", "manifest", "preview_video"):
        assert str(paths[key]).startswith(str(out_dir))


def test_windows_ass_path_escapes_drive_colon_once():
    import scripts.k3k6_visual_proof_preview as preview

    raw = r"C:\Users\alihu\AppData\Local\Temp\zenith_k3k6_visual_proof_1b\k3_caption_proof.ass"
    escaped = preview.escape_ffmpeg_filter_path(raw)

    assert escaped.startswith("C\\:/Users/")
    assert not escaped.startswith("C\\\\:/Users/")
    assert "\\" in escaped
    assert escaped.count("\\") == 1
    assert "\\Users" not in escaped
    assert "/Temp/zenith_k3k6_visual_proof_1b/k3_caption_proof.ass" in escaped


def test_subtitles_filter_uses_escaped_ass_path(monkeypatch):
    import scripts.k3k6_visual_proof_preview as preview

    monkeypatch.setattr(preview, "get_ffmpeg_path", lambda: "ffmpeg")
    raw = r"C:\Users\alihu\AppData\Local\Temp\zenith_k3k6_visual_proof_1b\k3_caption_proof.ass"

    command = preview.build_ffmpeg_command(
        "input.mp4",
        1.0,
        4.0,
        "output.mp4",
        raw,
    )
    vf = command[command.index("-vf") + 1]

    assert "subtitles='C\\:/Users/" in vf
    assert "C\\\\:/Users/" not in vf


def test_called_process_error_surfaces_stderr(monkeypatch):
    import pytest
    import scripts.k3k6_visual_proof_preview as preview

    def fake_run(command, capture_output, text, check):
        raise preview.subprocess.CalledProcessError(
            returncode=123,
            cmd=command,
            output="STDOUT_VISIBLE",
            stderr="STDERR_VISIBLE",
        )

    monkeypatch.setattr(preview.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as excinfo:
        preview.run_command(["ffmpeg", "-bad"])

    message = str(excinfo.value)
    assert "FFMPEG_PREVIEW_FAILED" in message
    assert "STDERR_VISIBLE" in message
    assert "STDOUT_VISIBLE" in message
    assert "ffmpeg" in message
