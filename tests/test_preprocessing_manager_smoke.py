from __future__ import annotations

from pathlib import Path

from core.preprocessing_manager import (
    apply_preprocessing_manifest_to_job,
    build_cache_key,
    build_source_fingerprint,
    load_preprocessing_manifest,
    prepare_preprocessing_workspace,
)
from models.job import Job
from models.preprocessing_manifest import PreprocessingManifest
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


def _make_manifest() -> PreprocessingManifest:
    return PreprocessingManifest(
        job_id="job_test_001",
        source_path="input.mp4",
        source_fingerprint={
            "path": "input.mp4",
            "exists": True,
            "size_bytes": 123,
            "mtime_ns": 456,
        },
        cache_key="abc123",
        preprocessed_dir="preprocessed/job_test_001",
        audio_dir="preprocessed/job_test_001/audio",
        frames_dir="preprocessed/job_test_001/frames",
        thumbnails_dir="preprocessed/job_test_001/thumbnails",
        temp_dir="preprocessed/job_test_001/temp",
        manifest_path="preprocessed/job_test_001/manifest.json",
        analysis_audio_path="preprocessed/job_test_001/audio/analysis.wav",
        speech_audio_path="preprocessed/job_test_001/audio/speech_16k_mono.wav",
        music_audio_path="preprocessed/job_test_001/audio/music_reference.wav",
        frame_pattern="preprocessed/job_test_001/frames/frame_%06d.jpg",
        thumbnail_pattern="preprocessed/job_test_001/thumbnails/thumb_%06d.jpg",
        status="ready",
        reused_cache=False,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        warnings=[],
        errors=[],
        metadata={"test": True},
    )


def _make_job() -> Job:
    return Job(
        job_id="job_test_001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="input.mp4",
    )


def test_preprocessing_manifest_roundtrip() -> None:
    manifest = _make_manifest()

    data = manifest.to_dict()
    restored = PreprocessingManifest.from_dict(data)

    assert restored.job_id == manifest.job_id
    assert restored.source_path == manifest.source_path
    assert restored.source_fingerprint == manifest.source_fingerprint
    assert restored.cache_key == manifest.cache_key
    assert restored.preprocessed_dir == manifest.preprocessed_dir
    assert restored.audio_dir == manifest.audio_dir
    assert restored.frames_dir == manifest.frames_dir
    assert restored.thumbnails_dir == manifest.thumbnails_dir
    assert restored.temp_dir == manifest.temp_dir
    assert restored.manifest_path == manifest.manifest_path
    assert restored.analysis_audio_path == manifest.analysis_audio_path
    assert restored.speech_audio_path == manifest.speech_audio_path
    assert restored.music_audio_path == manifest.music_audio_path
    assert restored.frame_pattern == manifest.frame_pattern
    assert restored.thumbnail_pattern == manifest.thumbnail_pattern
    assert restored.status == manifest.status
    assert restored.reused_cache == manifest.reused_cache
    assert restored.warnings == manifest.warnings
    assert restored.errors == manifest.errors
    assert restored.metadata == manifest.metadata


def test_build_source_fingerprint_existing_file(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_text("hello", encoding="utf-8")

    fingerprint = build_source_fingerprint(source)

    assert fingerprint["path"] == str(source)
    assert fingerprint["exists"] is True
    assert fingerprint["size_bytes"] == source.stat().st_size
    assert fingerprint["mtime_ns"] == source.stat().st_mtime_ns


def test_build_source_fingerprint_missing_file(tmp_path: Path) -> None:
    source = tmp_path / "missing.mp4"

    fingerprint = build_source_fingerprint(source)

    assert fingerprint["path"] == str(source)
    assert fingerprint["exists"] is False
    assert fingerprint["size_bytes"] is None
    assert fingerprint["mtime_ns"] is None


def test_prepare_preprocessing_workspace_creates_dirs_and_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_text("video-data", encoding="utf-8")

    root_dir = tmp_path / "preprocessed"

    manifest = prepare_preprocessing_workspace(
        job_id="job_test_001",
        source_path=source,
        root_dir=root_dir,
        metadata={"channel": "gaming_main"},
    )

    assert Path(manifest.preprocessed_dir).exists()
    assert Path(manifest.audio_dir).exists()
    assert Path(manifest.frames_dir).exists()
    assert Path(manifest.thumbnails_dir).exists()
    assert Path(manifest.temp_dir).exists()
    assert Path(manifest.manifest_path).exists()
    assert manifest.status == "ready"
    assert manifest.reused_cache is False
    assert manifest.metadata["channel"] == "gaming_main"


def test_load_preprocessing_manifest_works(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_text("video-data", encoding="utf-8")

    manifest = prepare_preprocessing_workspace(
        job_id="job_test_001",
        source_path=source,
        root_dir=tmp_path / "preprocessed",
    )

    loaded = load_preprocessing_manifest(manifest.manifest_path)

    assert loaded is not None
    assert loaded.job_id == manifest.job_id
    assert loaded.cache_key == manifest.cache_key


def test_prepare_preprocessing_workspace_reuses_cache_for_same_source(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_text("video-data", encoding="utf-8")

    root_dir = tmp_path / "preprocessed"

    first = prepare_preprocessing_workspace(
        job_id="job_test_001",
        source_path=source,
        root_dir=root_dir,
    )
    second = prepare_preprocessing_workspace(
        job_id="job_test_001",
        source_path=source,
        root_dir=root_dir,
    )

    assert first.cache_key == second.cache_key
    assert second.reused_cache is True


def test_prepare_preprocessing_workspace_rebuilds_cache_for_changed_source(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_text("video-data", encoding="utf-8")

    root_dir = tmp_path / "preprocessed"

    first = prepare_preprocessing_workspace(
        job_id="job_test_001",
        source_path=source,
        root_dir=root_dir,
    )

    source.write_text("video-data-changed-with-more-bytes", encoding="utf-8")

    second = prepare_preprocessing_workspace(
        job_id="job_test_001",
        source_path=source,
        root_dir=root_dir,
    )

    assert first.cache_key != second.cache_key
    assert second.reused_cache is False


def test_build_cache_key_is_stable_for_same_fingerprint() -> None:
    fingerprint = {
        "path": "input.mp4",
        "exists": True,
        "size_bytes": 123,
        "mtime_ns": 456,
    }

    first = build_cache_key(fingerprint)
    second = build_cache_key(dict(reversed(list(fingerprint.items()))))

    assert first == second
    assert len(first) == 24


def test_apply_preprocessing_manifest_to_job_sets_fields() -> None:
    job = _make_job()
    manifest = _make_manifest()

    apply_preprocessing_manifest_to_job(job, manifest)

    assert job.preprocessing_dir == manifest.preprocessed_dir
    assert job.preprocessing_manifest_path == manifest.manifest_path
    assert job.preprocessing_manifest == manifest.to_dict()
    assert job.preprocessing_status == manifest.status
    assert job.preprocessing_cache_key == manifest.cache_key
    assert job.preprocessing_reused_cache == manifest.reused_cache


def test_job_to_dict_from_dict_preserves_preprocessing_fields() -> None:
    job = _make_job()
    manifest = _make_manifest()
    apply_preprocessing_manifest_to_job(job, manifest)

    data = job.to_dict()
    restored = Job.from_dict(data)

    assert restored.preprocessing_dir == manifest.preprocessed_dir
    assert restored.preprocessing_manifest_path == manifest.manifest_path
    assert restored.preprocessing_manifest == manifest.to_dict()
    assert restored.preprocessing_status == manifest.status
    assert restored.preprocessing_cache_key == manifest.cache_key
    assert restored.preprocessing_reused_cache == manifest.reused_cache


def test_missing_source_manifest_has_error(tmp_path: Path) -> None:
    source = tmp_path / "missing.mp4"

    manifest = prepare_preprocessing_workspace(
        job_id="job_missing_source",
        source_path=source,
        root_dir=tmp_path / "preprocessed",
    )

    assert manifest.status == "missing_source"
    assert "source_missing" in manifest.errors
    assert Path(manifest.manifest_path).exists()


def test_preprocessing_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("models/preprocessing_manifest.py"),
        Path("core/preprocessing_manager.py"),
        Path("tests/test_preprocessing_manager_smoke.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"
