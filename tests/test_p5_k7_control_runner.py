from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import k7_control_runner as runner


def _make_source(tmp_path: Path, relative: str = "input/raw.mp4") -> Path:
    source = tmp_path / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"fake video bytes")
    return source


def _output_dir(tmp_path: Path, suffix: str = "case") -> Path:
    return tmp_path / "reports" / "phase5" / "k7_control_run" / suffix


def _run_dry(tmp_path: Path, source: Path | None = None, duration: float = 60.0) -> Path:
    source_path = source or _make_source(tmp_path)
    output = _output_dir(tmp_path)
    return runner.main(
        [
            "--source",
            str(source_path),
            "--output-dir",
            str(output),
            "--duration",
            str(duration),
            "--pair-id",
            "pair_001",
            "--dry-run",
        ]
    )


def _read_plan(plan_path: Path) -> dict[str, Any]:
    return json.loads(plan_path.read_text(encoding="utf-8"))


def _run_enabled_with_mock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, list[str]]:
    source = _make_source(tmp_path)
    output = _output_dir(tmp_path)
    calls: list[list[str]] = []

    def fake_run_ffmpeg_command(cmd: list[str]) -> None:
        calls.append(cmd)
        (output / runner.OUTPUT_VIDEO_FILENAME).write_bytes(b"fake mp4 bytes")

    monkeypatch.setattr(runner, "run_ffmpeg_command", fake_run_ffmpeg_command)

    manifest_path = runner.main(
        [
            "--source",
            str(source),
            "--output-dir",
            str(output),
            "--duration",
            "60",
            "--pair-id",
            "pair_001",
            "--enable-real-run",
        ]
    )

    assert calls
    return manifest_path, calls[0]


def test_dry_run_writes_plan_json(tmp_path: Path) -> None:
    plan_path = _run_dry(tmp_path)

    assert plan_path.name == "k7_control_plan.json"
    assert plan_path.exists()

    plan = _read_plan(plan_path)
    assert plan["status"] == "dry_run_ok"
    assert plan["duration"] == 60.0
    assert plan["pair_id"] == "pair_001"

    output_files = list(plan_path.parent.rglob("*"))
    assert not [path for path in output_files if path.suffix.lower() in {".mp4", ".mov", ".mkv"}]


@pytest.mark.parametrize("folder", ["reports", "exports", "shorts"])
def test_rejects_reports_exports_shorts_sources(tmp_path: Path, folder: str) -> None:
    source = _make_source(tmp_path, f"{folder}/raw.mp4")

    with pytest.raises(RuntimeError, match="K7_SOURCE_FORBIDDEN_LOCATION"):
        _run_dry(tmp_path, source=source)


@pytest.mark.parametrize("token", ["caption", "subtitle", "preview", "proof", "emoji"])
def test_rejects_captioned_or_preview_source_names(tmp_path: Path, token: str) -> None:
    source = _make_source(tmp_path, f"input/{token}_raw.mp4")

    with pytest.raises(RuntimeError, match="K7_SOURCE_FORBIDDEN_NAME_TOKEN"):
        _run_dry(tmp_path, source=source)


def test_duration_guard(tmp_path: Path) -> None:
    source = _make_source(tmp_path)

    with pytest.raises(RuntimeError, match="K7_DURATION_OUT_OF_RANGE"):
        _run_dry(tmp_path, source=source, duration=9.99)

    with pytest.raises(RuntimeError, match="K7_DURATION_OUT_OF_RANGE"):
        _run_dry(tmp_path, source=source, duration=120.1)

    plan_path = _run_dry(tmp_path, source=source, duration=60)
    assert _read_plan(plan_path)["duration"] == 60.0


def test_real_run_disabled(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    output = _output_dir(tmp_path)

    with pytest.raises(RuntimeError, match="K7_REAL_RUN_NOT_ENABLED_YET"):
        runner.main(
            [
                "--source",
                str(source),
                "--output-dir",
                str(output),
                "--duration",
                "60",
                "--pair-id",
                "pair_001",
            ]
        )


def test_pair_truth_ali_source_used(tmp_path: Path) -> None:
    plan_path = _run_dry(tmp_path)
    plan = _read_plan(plan_path)

    assert plan["ali_source"] == "a0"
    assert plan["friend_source"] == "a1"
    assert plan["game_source"] == "a2"
    assert plan["pair_truth_source"] == "video_configs/pair_track_truth.json"
    assert plan["legacy_trackmap_trusted"] is False

    source_text = Path(runner.__file__).read_text(encoding="utf-8")
    assert "speaker_distribution" not in source_text
    assert "track_mapping" not in source_text


def test_plan_disables_qwen_music_ingest_phase55(tmp_path: Path) -> None:
    plan = _read_plan(_run_dry(tmp_path))

    assert plan["qwen"] is False
    assert plan["music"] is False
    assert plan["ingest"] is False
    assert plan["phase5_5"] is False
    assert plan["full_batch"] is False


def test_output_dir_guard(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    bad_output = tmp_path / "not_allowed"

    with pytest.raises(RuntimeError, match="K7_OUTPUT_DIR_MUST_BE_UNDER_REPORTS_PHASE5_K7_CONTROL_RUN"):
        runner.main(
            [
                "--source",
                str(source),
                "--output-dir",
                str(bad_output),
                "--duration",
                "60",
                "--pair-id",
                "pair_001",
                "--dry-run",
            ]
        )


def test_real_run_requires_enable_flag(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    output = _output_dir(tmp_path)

    with pytest.raises(RuntimeError, match="K7_REAL_RUN_NOT_ENABLED_YET"):
        runner.main(
            [
                "--source",
                str(source),
                "--output-dir",
                str(output),
                "--duration",
                "60",
                "--pair-id",
                "pair_001",
            ]
        )


def test_enable_real_run_builds_expected_command_or_calls_renderer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path, cmd = _run_enabled_with_mock(tmp_path, monkeypatch)

    output_video = manifest_path.parent / runner.OUTPUT_VIDEO_FILENAME
    assert output_video.exists()
    assert manifest_path.name == runner.MANIFEST_FILENAME

    command_text = " ".join(cmd)
    assert runner.OUTPUT_VIDEO_FILENAME in command_text
    assert "-t" in cmd
    assert "60.000" in cmd
    assert "-an" not in cmd
    assert "s=1080x1920" in command_text
    assert "scale=1080" in command_text
    assert "-map" in cmd
    assert "0:a:0" in cmd


def test_real_run_manifest_contains_safety_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path, _cmd = _run_enabled_with_mock(tmp_path, monkeypatch)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["status"] == "ok"
    assert manifest["qwen"] is False
    assert manifest["music"] is False
    assert manifest["ingest"] is False
    assert manifest["phase5_5"] is False
    assert manifest["full_batch"] is False
    assert manifest["real_run_enabled"] is True
    assert manifest["clean_source_guard"] is True
    assert manifest["audio_present_expected"] is True
    assert manifest["captions_generated"] is False
    assert manifest["layout_or_reframe_applied"] is True
    assert manifest["ali_source"] == "a0"
    assert manifest["friend_source"] == "a1"
    assert manifest["game_source"] == "a2"
    assert manifest["next_step"] == "Ali eye/ear review"


def test_real_run_surfaces_ffmpeg_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    class Completed:
        returncode = 1
        stdout = "fake stdout"
        stderr = "fake ffmpeg stderr"

    monkeypatch.setattr(runner, "apply_ffmpeg_thread_cap", lambda cmd: cmd)
    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: Completed())

    with pytest.raises(RuntimeError) as error:
        runner.run_ffmpeg_command(["ffmpeg", "-version"])

    message = str(error.value)
    assert "K7_CONTROL_RUN_FAILED" in message
    assert "fake ffmpeg stderr" in message
    assert "fake stdout" in message


def test_no_old_unsafe_entrypoint_called() -> None:
    source_text = Path(runner.__file__).read_text(encoding="utf-8").casefold()

    blocked_terms = [
        "p5_g2_render_real_caption_shorts",
        "g2_s3b_render_pair001_multispeaker_sample",
        "g2_s3b_render_multispeaker_window",
        "p4_8_a4_reingest_pairs",
        "ol" + "lama",
        "api/" + "generate",
        "open" + "ai",
        "anthropic",
        "google",
    ]

    for term in blocked_terms:
        assert term.casefold() not in source_text

def test_real_run_ffmpeg_command_has_hard_duration_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest_path, cmd = _run_enabled_with_mock(tmp_path, monkeypatch)

    t_indices = [index for index, item in enumerate(cmd) if item == "-t"]
    assert len(t_indices) >= 2
    assert all(cmd[index + 1] == "60.000" for index in t_indices)


def test_color_source_is_duration_limited() -> None:
    filtergraph = runner.build_control_filter(60.0)

    color_terms = [part for part in filtergraph.split(";") if part.startswith("color=")]
    assert color_terms
    assert all(":d=60.000" in term for term in color_terms)
    assert "color=c=black:s=1080x1920[base]" not in filtergraph


def test_overlay_or_filtergraph_uses_shortest_or_trim() -> None:
    filtergraph = runner.build_control_filter(60.0)

    assert "trim=duration=60.000" in filtergraph
    assert "setpts=PTS-STARTPTS" in filtergraph
    assert "shortest=1" in filtergraph


def test_manifest_written_only_after_successful_ffmpeg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    success_manifest_path, _cmd = _run_enabled_with_mock(tmp_path, monkeypatch)
    assert success_manifest_path.exists()

    success_manifest = json.loads(success_manifest_path.read_text(encoding="utf-8"))
    assert success_manifest["status"] == "ok"

    failing_source = _make_source(tmp_path, "failure/raw.mp4")
    failing_output = _output_dir(tmp_path, "failure")

    def fake_failed_run_ffmpeg_command(cmd: list[str]) -> None:
        raise RuntimeError("K7_CONTROL_RUN_FAILED\nSTDOUT:\n\nSTDERR:\nfake ffmpeg failure")

    monkeypatch.setattr(runner, "run_ffmpeg_command", fake_failed_run_ffmpeg_command)

    with pytest.raises(RuntimeError, match="K7_CONTROL_RUN_FAILED"):
        runner.main(
            [
                "--source",
                str(failing_source),
                "--output-dir",
                str(failing_output),
                "--duration",
                "60",
                "--pair-id",
                "pair_001",
                "--enable-real-run",
            ]
        )

    assert not (failing_output / runner.MANIFEST_FILENAME).exists()


def test_real_run_does_not_disable_audio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manifest_path, cmd = _run_enabled_with_mock(tmp_path, monkeypatch)

    assert "-an" not in cmd
    assert "-map" in cmd
    assert "0:a:0" in cmd
