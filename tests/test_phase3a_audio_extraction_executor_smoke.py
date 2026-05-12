from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from core.audio_extraction_executor import (
    AudioExtractionResult,
    AudioExtractionTargetResult,
    apply_audio_extraction_result_to_job,
    apply_audio_extraction_result_to_manifest,
    execute_audio_extraction_plan,
)
from core.audio_extraction_planner import build_audio_extraction_plan
from core.ffmpeg_helper import get_ffmpeg_path
from core.preprocessing_manager import prepare_preprocessing_workspace
from models.audio_extraction_plan import AudioExtractionPlan, AudioExtractionTarget
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
    assert target_path.exists()
    assert target_path.stat().st_size > 0
    return target_path


def _make_job(raw_video_path: str) -> Job:
    return Job(
        job_id="job_phase3a_executor_smoke_001",
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


def test_executor_target_result_roundtrip() -> None:
    target = AudioExtractionTargetResult(
        target_id="analysis_audio",
        purpose="analysis",
        output_path="x.wav",
        status="ok",
        command=["ffmpeg", "-i", "in.wav", "x.wav"],
        returncode=0,
        output_size_bytes=1024,
    )

    data = target.to_dict()

    assert data["target_id"] == "analysis_audio"
    assert data["status"] == "ok"
    assert data["output_size_bytes"] == 1024
    assert data["command"] == ["ffmpeg", "-i", "in.wav", "x.wav"]


def test_executor_result_roundtrip() -> None:
    result = AudioExtractionResult(
        job_id="job_x",
        source_path="src.wav",
        audio_dir="audio/",
        status="ok",
        targets=[],
        ready_target_ids=["analysis_audio", "speech_audio"],
        missing_target_ids=[],
        failed_target_ids=[],
    )

    data = result.to_dict()

    assert data["status"] == "ok"
    assert data["ready_target_ids"] == ["analysis_audio", "speech_audio"]
    assert data["targets"] == []


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not available")
def test_executor_produces_real_wav_from_test_source(tmp_path: Path) -> None:
    source_path = _make_test_source(tmp_path / "source.wav", duration_seconds=1.0)

    manifest = prepare_preprocessing_workspace(
        job_id="job_phase3a_executor_smoke_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    plan = build_audio_extraction_plan(manifest=manifest)
    result = execute_audio_extraction_plan(plan=plan)

    assert isinstance(result, AudioExtractionResult)
    assert result.status in {"ok", "completed_with_warnings"}
    assert "analysis_audio" in result.ready_target_ids
    assert "speech_audio" in result.ready_target_ids
    assert not result.failed_target_ids

    analysis_path = Path(manifest.analysis_audio_path)
    speech_path = Path(manifest.speech_audio_path)

    assert analysis_path.exists()
    assert analysis_path.stat().st_size > 0
    assert speech_path.exists()
    assert speech_path.stat().st_size > 0


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not available")
def test_executor_reuses_existing_outputs_without_overwrite(tmp_path: Path) -> None:
    source_path = _make_test_source(tmp_path / "source.wav", duration_seconds=1.0)

    manifest = prepare_preprocessing_workspace(
        job_id="job_phase3a_executor_smoke_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    plan = build_audio_extraction_plan(manifest=manifest)
    first = execute_audio_extraction_plan(plan=plan)
    assert "analysis_audio" in first.ready_target_ids

    analysis_path = Path(manifest.analysis_audio_path)
    first_size = analysis_path.stat().st_size
    first_mtime = analysis_path.stat().st_mtime_ns

    second = execute_audio_extraction_plan(plan=plan, overwrite_existing=False)
    second_target_map = {t.target_id: t for t in second.targets}

    assert second_target_map["analysis_audio"].status == "skipped_existing_reusable"
    assert second_target_map["speech_audio"].status == "skipped_existing_reusable"
    assert analysis_path.stat().st_size == first_size
    assert analysis_path.stat().st_mtime_ns == first_mtime


def test_executor_blocks_when_source_missing(tmp_path: Path) -> None:
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    plan = AudioExtractionPlan(
        job_id="job_missing",
        source_path=str(tmp_path / "missing.mp4"),
        audio_dir=str(audio_dir),
        targets=[
            AudioExtractionTarget(
                target_id="analysis_audio",
                purpose="analysis",
                output_path=str(audio_dir / "analysis.wav"),
                sample_rate=44100,
                channels=2,
            ),
        ],
    )

    result = execute_audio_extraction_plan(plan=plan)

    target_map = {t.target_id: t for t in result.targets}
    assert target_map["analysis_audio"].status == "blocked_missing_source"
    assert "source_missing" in target_map["analysis_audio"].errors
    assert "analysis_audio" in result.missing_target_ids
    assert result.status in {"failed", "incomplete"}


def test_executor_skips_disabled_targets(tmp_path: Path) -> None:
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "fake.txt"
    source_path.write_text("nope", encoding="utf-8")

    plan = AudioExtractionPlan(
        job_id="job_disabled",
        source_path=str(source_path),
        audio_dir=str(audio_dir),
        targets=[
            AudioExtractionTarget(
                target_id="music_reference_audio",
                purpose="music_reference",
                output_path=str(audio_dir / "music_reference.wav"),
                enabled=False,
            ),
        ],
    )

    result = execute_audio_extraction_plan(plan=plan)

    target_map = {t.target_id: t for t in result.targets}
    assert target_map["music_reference_audio"].status == "skipped_disabled"


def test_executor_fails_cleanly_on_bad_source(tmp_path: Path) -> None:
    if not _ffmpeg_available():
        pytest.skip("ffmpeg not available")

    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    bad_source = tmp_path / "garbage.mp4"
    bad_source.write_text("not-a-real-video-file", encoding="utf-8")

    plan = AudioExtractionPlan(
        job_id="job_bad",
        source_path=str(bad_source),
        audio_dir=str(audio_dir),
        targets=[
            AudioExtractionTarget(
                target_id="analysis_audio",
                purpose="analysis",
                output_path=str(audio_dir / "analysis.wav"),
                sample_rate=44100,
                channels=2,
            ),
        ],
    )

    result = execute_audio_extraction_plan(plan=plan)

    target_map = {t.target_id: t for t in result.targets}
    assert target_map["analysis_audio"].status == "failed"
    assert "analysis_audio" in result.failed_target_ids
    assert result.status == "failed"


def test_apply_audio_extraction_result_to_manifest(tmp_path: Path) -> None:
    if not _ffmpeg_available():
        pytest.skip("ffmpeg not available")

    source_path = _make_test_source(tmp_path / "source.wav", duration_seconds=1.0)
    manifest = prepare_preprocessing_workspace(
        job_id="job_phase3a_executor_smoke_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )
    plan = build_audio_extraction_plan(manifest=manifest)
    result = execute_audio_extraction_plan(plan=plan)

    apply_audio_extraction_result_to_manifest(manifest, result)

    assert manifest.audio_extraction_result == result.to_dict()
    assert manifest.audio_extraction_status == result.status
    assert manifest.ready_audio_targets == result.ready_target_ids
    assert manifest.missing_audio_targets == result.missing_target_ids
    assert manifest.failed_audio_targets == result.failed_target_ids


def test_apply_audio_extraction_result_to_job(tmp_path: Path) -> None:
    if not _ffmpeg_available():
        pytest.skip("ffmpeg not available")

    source_path = _make_test_source(tmp_path / "source.wav", duration_seconds=1.0)
    manifest = prepare_preprocessing_workspace(
        job_id="job_phase3a_executor_smoke_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )
    plan = build_audio_extraction_plan(manifest=manifest)
    result = execute_audio_extraction_plan(plan=plan)

    job = _make_job(raw_video_path=str(source_path))
    apply_audio_extraction_result_to_job(job, result)

    assert job.audio_extraction_result == result.to_dict()
    assert job.audio_extraction_status == result.status
    assert job.ready_audio_targets == result.ready_target_ids

    restored = Job.from_dict(job.to_dict())
    assert restored.audio_extraction_result == job.audio_extraction_result
    assert restored.audio_extraction_status == job.audio_extraction_status
    assert restored.ready_audio_targets == job.ready_audio_targets
    assert restored.missing_audio_targets == job.missing_audio_targets
    assert restored.failed_audio_targets == job.failed_audio_targets


def test_old_job_dict_loads_without_audio_extraction_fields() -> None:
    legacy_data = {
        "job_id": "legacy_job_001",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }

    restored = Job.from_dict(legacy_data)

    assert restored.audio_extraction_result == {}
    assert restored.audio_extraction_status is None
    assert restored.ready_audio_targets == []
    assert restored.missing_audio_targets == []
    assert restored.failed_audio_targets == []


def test_old_manifest_dict_loads_without_audio_extraction_fields() -> None:
    from models.preprocessing_manifest import PreprocessingManifest

    legacy_data = {
        "job_id": "legacy_job_001",
        "source_path": "src.mp4",
        "source_fingerprint": {"path": "src.mp4"},
        "cache_key": "abc",
        "preprocessed_dir": "preprocessed/legacy",
        "audio_dir": "preprocessed/legacy/audio",
        "frames_dir": "preprocessed/legacy/frames",
        "thumbnails_dir": "preprocessed/legacy/thumbnails",
        "temp_dir": "preprocessed/legacy/temp",
        "manifest_path": "preprocessed/legacy/manifest.json",
        "analysis_audio_path": "preprocessed/legacy/audio/analysis.wav",
        "speech_audio_path": "preprocessed/legacy/audio/speech_16k_mono.wav",
        "music_audio_path": "preprocessed/legacy/audio/music_reference.wav",
        "frame_pattern": "preprocessed/legacy/frames/frame_%06d.jpg",
        "thumbnail_pattern": "preprocessed/legacy/thumbnails/thumb_%06d.jpg",
    }

    restored = PreprocessingManifest.from_dict(legacy_data)

    assert restored.audio_extraction_result == {}
    assert restored.audio_extraction_status is None
    assert restored.ready_audio_targets == []
    assert restored.missing_audio_targets == []
    assert restored.failed_audio_targets == []


def test_phase3a_executor_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("core/audio_extraction_executor.py"),
        Path("tests/test_phase3a_audio_extraction_executor_smoke.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"
