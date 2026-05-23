from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.smoke


REPO_ROOT = Path(__file__).resolve().parents[1]


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - depends on CI image
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return ffmpeg
        pytest.skip(f"ffmpeg unavailable for e2e smoke clip generation: {exc}")


def _write_smoke_clip(path: Path) -> None:
    cmd = [
        _ffmpeg_exe(),
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=1280x360:rate=10",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=44100",
        "-t",
        "5",
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "mpeg4",
        "-q:v",
        "5",
        "-c:a",
        "aac",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert path.is_file()


def test_pipeline_runner_e2e_smoke_does_not_raise_export_dir_unbound(
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    shutil.copytree(REPO_ROOT / "profiles", workdir / "profiles")
    video_path = workdir / "tmp" / "pipeline_runner_e2e_smoke.mp4"
    video_path.parent.mkdir()
    _write_smoke_clip(video_path)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["ZENITH_RENDER_GATE_AUTO_APPROVE"] = "1"

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "pipeline_runner.py"), str(video_path)],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    combined_output = f"{result.stdout}\n{result.stderr}"

    assert "[pipeline_runner] CLI JOB" in combined_output
    assert "[pipeline_runner] GAMING MAIN" in combined_output
    assert "RENDER_GATE OVERRIDE" in combined_output
    assert "reason=auto_approve_override" in combined_output
    assert "would_block=readiness_not_ready" in combined_output
    assert "[gaming_pipeline] VALIDATE" in combined_output
    assert "status=failed" in combined_output
    assert "[gaming_pipeline] DONE" in combined_output
    assert "status=validation_failed" in combined_output
    assert "ok=0" in combined_output
    assert "failed=1" in combined_output
    assert result.returncode != 0
    assert "UnboundLocalError" not in combined_output
    assert "cannot access local variable 'export_dir'" not in combined_output
    assert "Traceback" not in combined_output


def test_pipeline_runner_e2e_smoke_blocks_render_without_auto_approve(
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    shutil.copytree(REPO_ROOT / "profiles", workdir / "profiles")
    video_path = workdir / "tmp" / "pipeline_runner_e2e_noapprove_smoke.mp4"
    video_path.parent.mkdir()
    _write_smoke_clip(video_path)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["ZENITH_RENDER_GATE_AUTO_APPROVE"] = "0"

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "pipeline_runner.py"), str(video_path)],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    combined_output = f"{result.stdout}\n{result.stderr}"

    assert "[pipeline_runner] CLI JOB" in combined_output
    assert "[pipeline_runner] GAMING MAIN" in combined_output
    assert "[gaming_pipeline] RENDER_GATE BLOCKED" in combined_output
    assert "reason=readiness_not_ready" in combined_output
    assert "status=render_blocked" in combined_output
    assert "ok=0" in combined_output
    assert "failed=1" in combined_output
    assert "[gaming_pipeline] RENDER    " not in combined_output
    assert result.returncode != 0
    assert "UnboundLocalError" not in combined_output
    assert "Traceback" not in combined_output
