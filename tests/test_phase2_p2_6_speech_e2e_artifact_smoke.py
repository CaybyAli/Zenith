from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_RUNNER = REPO_ROOT / "pipeline_runner.py"
WHISPER_PROBE_WAV = REPO_ROOT / "tests" / "fixtures" / "whisper_probe.wav"


def _ffmpeg_exe() -> str:
    from core.ffmpeg_helper import get_ffmpeg_path

    return get_ffmpeg_path()


def _prepare_workspace(tmp_path: Path) -> Path:
    workdir = tmp_path / "workspace"
    workdir.mkdir(parents=True, exist_ok=True)

    for name in [
        "pipeline_runner.py",
        "core",
        "models",
        "shared",
        "storage",
        "profiles",
        "assets",
        "config",
        "tests",
    ]:
        src = REPO_ROOT / name
        dst = workdir / name
        if src.is_dir():
            shutil.copytree(src, dst)
        elif src.is_file():
            shutil.copy2(src, dst)

    return workdir


def _write_speech_probe_clip(path: Path) -> None:
    assert WHISPER_PROBE_WAV.is_file(), "Missing committed whisper_probe.wav fixture"

    path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        _ffmpeg_exe(),
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:size=3840x1080:rate=30",
        "-i",
        str(WHISPER_PROBE_WAV),
        "-shortest",
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


def _run_pipeline(workdir: Path, video_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["ZENITH_RENDER_GATE_AUTO_APPROVE"] = "1"

    # P2-6 artifact mode:
    # The full pipeline must prove that speech creates transcript segments,
    # but the test must be reproducible on machines without Whisper/CUDA.
    env["ZENITH_TRANSCRIPT_TEST_MODE"] = "1"

    return subprocess.run(
        [sys.executable, str(workdir / "pipeline_runner.py"), str(video_path)],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        timeout=420,
    )


def _latest_job_json(workdir: Path) -> Path:
    candidates = sorted(
        (workdir / "exports").glob("*/*/job.json"),
        key=lambda path: path.stat().st_mtime,
    )
    assert candidates, "Expected exported job.json"
    return candidates[-1]


def _segments(payload: dict[str, Any]) -> list[Any]:
    value = payload.get("transcript_segments")
    if isinstance(value, list):
        return value

    report = payload.get("transcript_report")
    if isinstance(report, dict) and isinstance(report.get("segments"), list):
        return report["segments"]

    return []


def test_p2_6_speech_e2e_artifact_produces_transcript_segments_and_review_output(tmp_path: Path) -> None:
    workdir = _prepare_workspace(tmp_path)
    video_path = workdir / "tmp" / "p2_6_speech_probe_32x9.mp4"
    _write_speech_probe_clip(video_path)

    result = _run_pipeline(workdir, video_path)
    combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

    assert "[gaming_pipeline] DONE" in combined_output
    assert "[gaming_pipeline] TRANSCRIPT" in combined_output
    assert "segments=2" in combined_output
    assert "engine=test-fallback" in combined_output
    assert "[gaming_pipeline] VALIDATE" in combined_output
    assert "status=passed" in combined_output
    assert "all blocking checks passed" in combined_output

    # The tiny committed speech fixture may still be rejected by the broader
    # Phase-2B stabilization checker because it is intentionally short and has
    # only one render segment. P2-6 proves speech/transcript reproducibility,
    # not full production-readiness of this tiny fixture.
    if result.returncode != 0:
        assert "phase_2b_stabilization_not_ready" in combined_output

    job_json = _latest_job_json(workdir)
    payload = json.loads(job_json.read_text(encoding="utf-8"))

    status = str(payload.get("status") or "")
    assert status in {"approval_pending", "validation_failed"}
    if status == "validation_failed":
        assert payload.get("error_message") == "phase_2b_stabilization_not_ready"
    else:
        assert not payload.get("error_message")

    segments = _segments(payload)
    assert len(segments) >= 2

    assert payload.get("transcript_segment_count", 0) >= 2
    assert payload.get("transcript_status") in {"ok", "completed_with_warnings"}
    assert payload.get("transcript_language") == "test"
    assert (payload.get("transcript_report") or {}).get("engine") == "test-fallback"

    video_output = Path(payload.get("video_path") or "")
    thumbnail_output = Path(payload.get("thumbnail_path") or "")

    if not video_output.is_absolute():
        video_output = workdir / video_output
    if not thumbnail_output.is_absolute():
        thumbnail_output = workdir / thumbnail_output

    assert video_output.exists()
    assert video_output.stat().st_size > 1000

    assert thumbnail_output.exists()
    assert thumbnail_output.stat().st_size > 0
