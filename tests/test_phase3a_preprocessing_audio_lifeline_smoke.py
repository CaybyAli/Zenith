from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from core.ffmpeg_helper import get_ffmpeg_path
from core.preprocessing_pipeline import (
    build_preprocessing_pipeline_report,
    run_preprocessing_pipeline_for_job,
)
from models.job import Job
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


def _ffmpeg_available() -> bool:
    try:
        get_ffmpeg_path()
        return True
    except FileNotFoundError:
        return False


def _require_ffmpeg() -> str:
    try:
        return get_ffmpeg_path()
    except FileNotFoundError:
        pytest.skip("ffmpeg not available on this system")


def _make_test_source(target_path: Path, duration_seconds: float = 1.0) -> Path:
    ffmpeg = _require_ffmpeg()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-loglevel", "error",
        "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration_seconds}",
        "-ar", "44100",
        "-ac", "2",
        "-c:a", "pcm_s16le",
        str(target_path),
    ]
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return target_path


def _make_job(raw_video_path: str) -> Job:
    return Job(
        job_id="job_phase3a_lifeline_001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path=raw_video_path,
    )


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not available")
def test_pipeline_produces_real_analysis_and_speech_wav(tmp_path: Path) -> None:
    source_path = _make_test_source(tmp_path / "source.wav", duration_seconds=1.0)

    report = build_preprocessing_pipeline_report(
        job_id="job_phase3a_lifeline_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
        metadata={"stage": "3-A"},
    )

    assert report["status"] in {"ready", "ready_with_warnings"}
    assert report["audio_extraction_status"] in {"ok", "completed_with_warnings"}

    manifest_dict = report["preprocessing_manifest"]
    analysis_path = Path(manifest_dict["analysis_audio_path"])
    speech_path = Path(manifest_dict["speech_audio_path"])

    assert analysis_path.exists()
    assert analysis_path.stat().st_size > 0
    assert speech_path.exists()
    assert speech_path.stat().st_size > 0

    assert "analysis_audio" in report["ready_audio_targets"]
    assert "speech_audio" in report["ready_audio_targets"]


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not available")
def test_pipeline_manifest_json_contains_audio_extraction_result(tmp_path: Path) -> None:
    source_path = _make_test_source(tmp_path / "source.wav", duration_seconds=1.0)

    report = build_preprocessing_pipeline_report(
        job_id="job_phase3a_lifeline_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    manifest_path = Path(report["manifest_path"])
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert data["audio_extraction_result"]
    assert data["audio_extraction_status"] in {"ok", "completed_with_warnings"}
    assert "analysis_audio" in data["ready_audio_targets"]
    assert "speech_audio" in data["ready_audio_targets"]
    assert data["audio_extraction_result"]["targets"]


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not available")
def test_pipeline_cache_validation_marks_audio_targets_ready(tmp_path: Path) -> None:
    source_path = _make_test_source(tmp_path / "source.wav", duration_seconds=1.0)

    report = build_preprocessing_pipeline_report(
        job_id="job_phase3a_lifeline_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    cache_validation = report["cache_validation"]
    ready_targets = list(cache_validation.get("ready_targets") or [])
    missing_targets = list(cache_validation.get("missing_targets") or [])

    assert "analysis_audio" in ready_targets
    assert "speech_audio" in ready_targets
    assert "analysis_audio" not in missing_targets
    assert "speech_audio" not in missing_targets


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not available")
def test_pipeline_sets_audio_extraction_fields_on_job(tmp_path: Path) -> None:
    source_path = _make_test_source(tmp_path / "source.wav", duration_seconds=1.0)
    job = _make_job(raw_video_path=str(source_path))

    report = run_preprocessing_pipeline_for_job(
        job=job,
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    assert job.audio_extraction_result == report["audio_extraction_result"]
    assert job.audio_extraction_status == report["audio_extraction_status"]
    assert job.ready_audio_targets == list(report["ready_audio_targets"])
    assert job.missing_audio_targets == list(report["missing_audio_targets"])
    assert job.failed_audio_targets == list(report["failed_audio_targets"])

    assert "analysis_audio" in job.ready_audio_targets
    assert "speech_audio" in job.ready_audio_targets

    restored = Job.from_dict(job.to_dict())
    assert restored.audio_extraction_result == job.audio_extraction_result
    assert restored.audio_extraction_status == job.audio_extraction_status
    assert restored.ready_audio_targets == job.ready_audio_targets


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not available")
def test_pipeline_reruns_reuse_existing_outputs(tmp_path: Path) -> None:
    source_path = _make_test_source(tmp_path / "source.wav", duration_seconds=1.0)

    first = build_preprocessing_pipeline_report(
        job_id="job_phase3a_lifeline_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )
    analysis_path = Path(first["preprocessing_manifest"]["analysis_audio_path"])
    first_mtime = analysis_path.stat().st_mtime_ns

    second = build_preprocessing_pipeline_report(
        job_id="job_phase3a_lifeline_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    second_targets = {
        t["target_id"]: t
        for t in second["audio_extraction_result"]["targets"]
    }

    assert second_targets["analysis_audio"]["status"] == "skipped_existing_reusable"
    assert second_targets["speech_audio"]["status"] == "skipped_existing_reusable"
    assert analysis_path.stat().st_mtime_ns == first_mtime


def test_pipeline_fails_cleanly_when_source_is_unreadable_video(tmp_path: Path) -> None:
    if not _ffmpeg_available():
        pytest.skip("ffmpeg not available")

    source_path = tmp_path / "broken.mp4"
    source_path.write_text("not-a-real-video", encoding="utf-8")

    report = build_preprocessing_pipeline_report(
        job_id="job_phase3a_lifeline_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    assert report["status"] == "failed"
    assert report["audio_extraction_status"] == "failed"
    assert "analysis_audio" in report["failed_audio_targets"]
    assert "speech_audio" in report["failed_audio_targets"]


def test_pipeline_missing_source_reports_blocked_targets(tmp_path: Path) -> None:
    source_path = tmp_path / "does_not_exist.mp4"

    report = build_preprocessing_pipeline_report(
        job_id="job_phase3a_lifeline_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    assert report["status"] == "failed"
    assert "source_missing" in report["errors"]
    missing_or_failed = (
        set(report["missing_audio_targets"]) | set(report["failed_audio_targets"])
    )
    assert "analysis_audio" in missing_or_failed
    assert "speech_audio" in missing_or_failed


def test_pipeline_can_disable_audio_extraction(tmp_path: Path) -> None:
    source_path = tmp_path / "source.mp4"
    source_path.write_text("placeholder", encoding="utf-8")

    report = build_preprocessing_pipeline_report(
        job_id="job_phase3a_lifeline_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
        execute_audio_extraction=False,
    )

    assert report["audio_extraction_result"] == {}
    assert report["audio_extraction_status"] is None
    assert report["ready_audio_targets"] == []
    assert report["missing_audio_targets"] == []
    assert report["failed_audio_targets"] == []


def test_phase3a_lifeline_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("core/audio_extraction_executor.py"),
        Path("core/preprocessing_pipeline.py"),
        Path("models/preprocessing_manifest.py"),
        Path("models/job.py"),
        Path("tests/test_phase3a_audio_extraction_executor_smoke.py"),
        Path("tests/test_phase3a_preprocessing_audio_lifeline_smoke.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"


def test_preprocessing_pipeline_source_imports_executor() -> None:
    source = Path("core/preprocessing_pipeline.py").read_text(encoding="utf-8")
    assert "audio_extraction_executor" in source
    assert "execute_audio_extraction_plan" in source
    assert "apply_audio_extraction_result_to_manifest" in source
