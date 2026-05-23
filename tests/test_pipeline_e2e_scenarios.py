from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.smoke


REPO_ROOT = Path(__file__).resolve().parents[1]
WHISPER_PROBE_WAV = REPO_ROOT / "tests" / "fixtures" / "whisper_probe.wav"


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - depends on local image
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return ffmpeg
        pytest.skip(f"ffmpeg unavailable for e2e scenario clip generation: {exc}")


def _prepare_workspace(tmp_path: Path) -> Path:
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    shutil.copytree(REPO_ROOT / "profiles", workdir / "profiles")
    return workdir


def _run_pipeline(
    workdir: Path,
    video_path: Path | None = None,
    *,
    auto_approve: bool = True,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["ZENITH_RENDER_GATE_AUTO_APPROVE"] = "1" if auto_approve else "0"

    cmd = [sys.executable, str(REPO_ROOT / "pipeline_runner.py")]
    if video_path is not None:
        cmd.append(str(video_path))

    return subprocess.run(
        cmd,
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return f"{result.stdout}\n{result.stderr}"


def _assert_no_python_crash(combined_output: str) -> None:
    assert "Traceback" not in combined_output
    assert "UnboundLocalError" not in combined_output
    assert "cannot access local variable" not in combined_output


def _latest_exported_job_json(workdir: Path) -> Path:
    candidates = sorted(
        (workdir / "exports").glob("*/*/job.json"),
        key=lambda path: path.stat().st_mtime,
    )
    assert candidates, "Expected an exported job.json to document the E2E result"
    return candidates[-1]


def _load_latest_job_payload(workdir: Path) -> dict[str, Any]:
    path = _latest_exported_job_json(workdir)
    return json.loads(path.read_text(encoding="utf-8"))


def _job_status(payload: dict[str, Any]) -> str:
    value = payload.get("status") or payload.get("job_status") or ""
    if isinstance(value, dict):
        value = value.get("value") or value.get("name") or str(value)
    return str(value)


def _write_silent_blue_clip(path: Path, duration: int = 5) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _ffmpeg_exe(),
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:size=1280x360:rate=10",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=mono:sample_rate=44100",
        "-t",
        str(duration),
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


def _write_motion_tone_clip(path: Path, duration: int = 5) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
        str(duration),
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


def _write_speech_probe_clip(path: Path) -> None:
    assert WHISPER_PROBE_WAV.is_file(), "Missing committed whisper_probe.wav fixture"
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _ffmpeg_exe(),
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:size=160x90:rate=10",
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


def _transcript_segments(payload: dict[str, Any]) -> list[Any]:
    segments = payload.get("transcript_segments")
    if isinstance(segments, list):
        return segments
    report = payload.get("transcript_report")
    if isinstance(report, dict) and isinstance(report.get("segments"), list):
        return report["segments"]
    return []


def _skip_if_real_whisper_fixture_unavailable() -> None:
    from core.transcript_processor import TranscriptProcessor, TranscriptUnavailableError

    if not WHISPER_PROBE_WAV.is_file():
        pytest.skip(f"Whisper fixture missing: {WHISPER_PROBE_WAV}")

    old_test_mode = os.environ.pop("ZENITH_TRANSCRIPT_TEST_MODE", None)
    old_hf_offline = os.environ.get("HF_HUB_OFFLINE")
    old_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    try:
        result = TranscriptProcessor().transcribe(str(WHISPER_PROBE_WAV))
        if not (result.segments or []):
            pytest.skip("Real Whisper fixture produced no transcript segments in this environment")
    except (TranscriptUnavailableError, ImportError, RuntimeError, OSError) as exc:
        pytest.skip(f"Real Whisper fixture unavailable in this environment: {exc}")
    finally:
        if old_test_mode is not None:
            os.environ["ZENITH_TRANSCRIPT_TEST_MODE"] = old_test_mode

        if old_hf_offline is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = old_hf_offline

        if old_transformers_offline is None:
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
        else:
            os.environ["TRANSFORMERS_OFFLINE"] = old_transformers_offline


def test_s1_pipeline_handles_silent_video_without_speech(tmp_path: Path) -> None:
    workdir = _prepare_workspace(tmp_path)
    video_path = workdir / "tmp" / "s1_silent_blue.mp4"
    _write_silent_blue_clip(video_path)

    result = _run_pipeline(workdir, video_path, auto_approve=True)
    combined_output = _combined_output(result)
    job_payload = _load_latest_job_payload(workdir)

    assert "[pipeline_runner] CLI JOB" in combined_output
    assert "[pipeline_runner] GAMING MAIN" in combined_output
    assert "[gaming_pipeline] DONE" in combined_output
    assert "status=" in combined_output
    assert "failed=1" in combined_output
    _assert_no_python_crash(combined_output)

    status = _job_status(job_payload).lower()
    assert status != "crashed", combined_output

    assert _transcript_segments(job_payload) == []
    transcript_status = str(job_payload.get("transcript_status") or "").lower()
    profanity_status = str(job_payload.get("profanity_censor_status") or "").lower()

    assert (
        "TRANSCRIPT_SKIPPED" in combined_output
        or "TRANSCRIPT_BLOCKED" in combined_output
        or "no_valid_transcript" in transcript_status
        or "skipped" in transcript_status
        or "unavailable" in transcript_status
        or transcript_status in {"", "skipped_no_transcript_segments"}
    )
    assert (
        "PROFANITY_CENSOR_SKIPPED" in combined_output
        or profanity_status == "skipped_no_transcript_segments"
        or job_payload.get("profanity_censor_match_count", 0) == 0
    )


@pytest.mark.real_whisper
def test_s2_pipeline_handles_video_with_whisper_probe_speech(tmp_path: Path) -> None:
    _skip_if_real_whisper_fixture_unavailable()
    workdir = _prepare_workspace(tmp_path)
    video_path = workdir / "tmp" / "s2_whisper_probe.mp4"
    _write_speech_probe_clip(video_path)

    result = _run_pipeline(workdir, video_path, auto_approve=True, timeout=420)
    combined_output = _combined_output(result)
    job_payload = _load_latest_job_payload(workdir)

    assert "[pipeline_runner] CLI JOB" in combined_output
    assert "[pipeline_runner] GAMING MAIN" in combined_output
    assert "[gaming_pipeline] DONE" in combined_output
    _assert_no_python_crash(combined_output)

    status = _job_status(job_payload).lower()
    assert status != "crashed", combined_output

    segments = _transcript_segments(job_payload)
    assert len(segments) >= 1, (
        "Expected whisper_probe.wav wrapped into MP4 to produce at least "
        "one transcript segment"
    )


def test_s3_thumbnail_fallback_removes_missing_thumbnail_blocker_after_auto_approve(tmp_path: Path) -> None:
    workdir = _prepare_workspace(tmp_path)
    video_path = workdir / "tmp" / "s3_missing_thumbnail.mp4"
    _write_motion_tone_clip(video_path)

    result = _run_pipeline(workdir, video_path, auto_approve=True)
    combined_output = _combined_output(result)
    job_payload = _load_latest_job_payload(workdir)
    serialized_job = json.dumps(job_payload, ensure_ascii=False)

    assert "RENDER_GATE OVERRIDE" in combined_output
    assert "reason=auto_approve_override" in combined_output
    assert "[gaming_pipeline] VALIDATE" in combined_output
    assert "[gaming_pipeline] DONE" in combined_output
    _assert_no_python_crash(combined_output)

    assert "Missing thumbnail" not in combined_output
    assert "Missing thumbnail" not in serialized_job

    thumbnail_path = job_payload.get("thumbnail_path")
    assert thumbnail_path, "Expected P2-5 thumbnail fallback to set job.thumbnail_path"

    thumbnail_file = Path(thumbnail_path)
    if not thumbnail_file.is_absolute():
        thumbnail_file = workdir / thumbnail_file

    assert thumbnail_file.exists(), f"Expected thumbnail file to exist: {thumbnail_file}"
    assert thumbnail_file.stat().st_size > 0

    assert "THUMBNAIL_FALLBACK_CREATED" in combined_output or "thumbnail_path" in serialized_job

    # The job may still fail on later Phase-2B stabilization gates, but not because
    # the thumbnail is missing anymore.
    if result.returncode != 0:
        assert (
            "phase_2b_stabilization_not_ready" in combined_output
            or "phase_2b_stabilization_not_ready" in serialized_job
        )

def test_s6_inbox_rerun_skips_existing_job(tmp_path: Path) -> None:
    workdir = _prepare_workspace(tmp_path)
    inbox_video = workdir / "inbox" / "gaming_main" / "s6_rerun_existing.mp4"
    _write_motion_tone_clip(inbox_video)

    first = _run_pipeline(workdir, video_path=None, auto_approve=True)
    first_output = _combined_output(first)

    assert "[pipeline_runner] INBOX NEW" in first_output
    assert "[pipeline_runner] INBOX JOB" in first_output
    assert "[pipeline_runner] GAMING MAIN" in first_output
    _assert_no_python_crash(first_output)

    second = _run_pipeline(workdir, video_path=None, auto_approve=True)
    second_output = _combined_output(second)

    assert "[pipeline_runner] INBOX SKIP" in second_output
    assert "(job already exists)" in second_output
    assert "[pipeline_runner] Keine aktuellen Rohdateien." in second_output
    assert second.returncode == 0
    _assert_no_python_crash(second_output)


def test_s7_profanity_e2e_placeholder() -> None:
    pytest.skip(
        "S7 skipped intentionally: Profanity Censor is transcript-token based, "
        "not audio-SFX based. A real E2E trigger needs a controlled speech "
        "fixture that Whisper reliably transcribes to a configured term such "
        "as 'severe_token', 'scheiss', 'damn', or 'crap'."
    )

