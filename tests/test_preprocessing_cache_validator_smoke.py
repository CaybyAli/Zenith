from __future__ import annotations

from pathlib import Path

from core.preprocessing_cache_validator import (
    apply_cache_validation_to_job,
    apply_cache_validation_to_manifest,
    validate_preprocessing_cache,
)
from core.preprocessing_manager import build_cache_key, build_source_fingerprint
from models.job import Job
from models.preprocessing_cache_validation import PreprocessingCacheValidationResult
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


def _make_job() -> Job:
    return Job(
        job_id="job_cache_001",
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


def _make_manifest(
    tmp_path: Path,
    source_exists: bool = True,
    make_workspace: bool = True,
    include_plans: bool = True,
    include_targets: bool = False,
    cache_key_override: str | None = None,
) -> PreprocessingManifest:
    source_path = tmp_path / "input.mp4"

    if source_exists:
        source_path.write_text("video-data", encoding="utf-8")

    fingerprint = build_source_fingerprint(source_path)
    cache_key = cache_key_override or build_cache_key(fingerprint)

    base = tmp_path / "preprocessed" / "job_cache_001"
    audio_dir = base / "audio"
    frames_dir = base / "frames"
    thumbnails_dir = base / "thumbnails"
    temp_dir = base / "temp"

    if make_workspace:
        audio_dir.mkdir(parents=True, exist_ok=True)
        frames_dir.mkdir(parents=True, exist_ok=True)
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

    audio_targets = []
    frame_targets = []

    if include_targets:
        audio_targets = [
            {
                "target_id": "analysis_audio",
                "purpose": "analysis",
                "output_path": str(audio_dir / "analysis.wav"),
                "format": "wav",
                "sample_rate": 44100,
                "channels": 2,
                "enabled": True,
                "status": "planned",
            }
        ]
        frame_targets = [
            {
                "target_id": "analysis_frames",
                "purpose": "analysis",
                "output_pattern": str(frames_dir / "frame_%06d.jpg"),
                "format": "jpg",
                "interval_seconds": 1.0,
                "enabled": True,
                "status": "planned",
            }
        ]

    return PreprocessingManifest(
        job_id="job_cache_001",
        source_path=str(source_path),
        source_fingerprint=fingerprint,
        cache_key=cache_key,
        preprocessed_dir=str(base),
        audio_dir=str(audio_dir),
        frames_dir=str(frames_dir),
        thumbnails_dir=str(thumbnails_dir),
        temp_dir=str(temp_dir),
        manifest_path=str(base / "manifest.json"),
        analysis_audio_path=str(audio_dir / "analysis.wav"),
        speech_audio_path=str(audio_dir / "speech_16k_mono.wav"),
        music_audio_path=str(audio_dir / "music_reference.wav"),
        frame_pattern=str(frames_dir / "frame_%06d.jpg"),
        thumbnail_pattern=str(thumbnails_dir / "thumb_%06d.jpg"),
        audio_extraction_plan={"status": "planned"} if include_plans else {},
        audio_targets=audio_targets,
        frame_extraction_plan={"status": "planned"} if include_plans else {},
        frame_targets=frame_targets,
        status="ready" if source_exists else "missing_source",
        reused_cache=False,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        warnings=[],
        errors=["source_missing"] if not source_exists else [],
        metadata={"test": True},
    )


def test_preprocessing_cache_validation_result_roundtrip() -> None:
    result = PreprocessingCacheValidationResult(
        reusable=True,
        status="reusable_with_warnings",
        severity="warning",
        cache_key="abc",
        expected_cache_key="abc",
        manifest_path="preprocessed/job/manifest.json",
        source_path="input.mp4",
        missing_paths=["missing"],
        existing_paths=["existing"],
        missing_targets=["analysis_audio"],
        ready_targets=["analysis_frames"],
        warnings=["target_output_missing"],
        errors=[],
        recommendation="reuse_with_review",
        details={"reason": "test"},
    )

    restored = PreprocessingCacheValidationResult.from_dict(result.to_dict())

    assert restored.reusable == result.reusable
    assert restored.status == result.status
    assert restored.severity == result.severity
    assert restored.cache_key == result.cache_key
    assert restored.expected_cache_key == result.expected_cache_key
    assert restored.manifest_path == result.manifest_path
    assert restored.source_path == result.source_path
    assert restored.missing_paths == result.missing_paths
    assert restored.existing_paths == result.existing_paths
    assert restored.missing_targets == result.missing_targets
    assert restored.ready_targets == result.ready_targets
    assert restored.warnings == result.warnings
    assert restored.errors == result.errors
    assert restored.recommendation == result.recommendation
    assert restored.details == result.details


def test_missing_manifest_is_not_reusable() -> None:
    result = validate_preprocessing_cache(None)

    assert result.reusable is False
    assert result.status == "missing_manifest"
    assert result.severity == "error"
    assert "manifest_missing" in result.errors
    assert result.recommendation == "rebuild"


def test_source_missing_is_not_reusable(tmp_path: Path) -> None:
    manifest = _make_manifest(tmp_path, source_exists=False)

    result = validate_preprocessing_cache(manifest)

    assert result.reusable is False
    assert "source_missing" in result.errors


def test_cache_key_mismatch_requires_rebuild(tmp_path: Path) -> None:
    manifest = _make_manifest(
        tmp_path,
        source_exists=True,
        cache_key_override="wrong-cache-key",
    )

    result = validate_preprocessing_cache(manifest)

    assert result.reusable is False
    assert result.status == "rebuild_required"
    assert result.severity == "error"
    assert "cache_key_mismatch" in result.errors
    assert result.recommendation == "rebuild"


def test_complete_workspace_is_reusable_with_plan_warnings_or_ok(tmp_path: Path) -> None:
    manifest = _make_manifest(
        tmp_path,
        source_exists=True,
        make_workspace=True,
        include_plans=True,
        include_targets=False,
    )

    result = validate_preprocessing_cache(manifest)

    assert result.reusable is True
    assert result.errors == []
    assert result.status in ["reusable", "reusable_with_warnings"]
    assert str(Path(manifest.preprocessed_dir)) in result.existing_paths
    assert str(Path(manifest.audio_dir)) in result.existing_paths
    assert str(Path(manifest.frames_dir)) in result.existing_paths
    assert str(Path(manifest.thumbnails_dir)) in result.existing_paths
    assert str(Path(manifest.temp_dir)) in result.existing_paths


def test_missing_audio_and_frame_plans_add_warnings(tmp_path: Path) -> None:
    manifest = _make_manifest(
        tmp_path,
        source_exists=True,
        make_workspace=True,
        include_plans=False,
    )

    result = validate_preprocessing_cache(manifest)

    assert result.reusable is True
    assert result.status == "reusable_with_warnings"
    assert result.severity == "warning"
    assert "audio_extraction_plan_missing" in result.warnings
    assert "frame_extraction_plan_missing" in result.warnings


def test_missing_enabled_audio_target_is_warning_not_error(tmp_path: Path) -> None:
    manifest = _make_manifest(
        tmp_path,
        source_exists=True,
        make_workspace=True,
        include_plans=True,
        include_targets=True,
    )

    result = validate_preprocessing_cache(manifest)

    assert result.reusable is True
    assert result.status == "reusable_with_warnings"
    assert "target_output_missing" in result.warnings
    assert "analysis_audio" in result.missing_targets
    assert result.errors == []


def test_frame_pattern_parent_dir_counts_as_ready(tmp_path: Path) -> None:
    manifest = _make_manifest(
        tmp_path,
        source_exists=True,
        make_workspace=True,
        include_plans=True,
        include_targets=True,
    )

    result = validate_preprocessing_cache(manifest)

    assert "analysis_frames" in result.ready_targets


def test_apply_cache_validation_to_manifest_sets_fields(tmp_path: Path) -> None:
    manifest = _make_manifest(tmp_path)
    validation = validate_preprocessing_cache(manifest)

    apply_cache_validation_to_manifest(manifest, validation)

    assert manifest.cache_validation == validation.to_dict()
    assert manifest.cache_validation_status == validation.status
    assert manifest.cache_reuse_allowed == validation.reusable


def test_apply_cache_validation_to_job_sets_fields(tmp_path: Path) -> None:
    manifest = _make_manifest(tmp_path)
    validation = validate_preprocessing_cache(manifest)
    job = _make_job()

    apply_cache_validation_to_job(job, validation)

    assert job.preprocessing_cache_validation == validation.to_dict()
    assert job.preprocessing_cache_validation_status == validation.status
    assert job.preprocessing_cache_reuse_allowed == validation.reusable


def test_job_to_dict_from_dict_preserves_cache_validation_fields(tmp_path: Path) -> None:
    manifest = _make_manifest(tmp_path)
    validation = validate_preprocessing_cache(manifest)
    job = _make_job()

    apply_cache_validation_to_job(job, validation)
    restored = Job.from_dict(job.to_dict())

    assert restored.preprocessing_cache_validation == validation.to_dict()
    assert restored.preprocessing_cache_validation_status == validation.status
    assert restored.preprocessing_cache_reuse_allowed == validation.reusable


def test_preprocessing_manifest_roundtrip_preserves_cache_validation_fields(
    tmp_path: Path,
) -> None:
    manifest = _make_manifest(tmp_path)
    validation = validate_preprocessing_cache(manifest)

    apply_cache_validation_to_manifest(manifest, validation)
    restored = PreprocessingManifest.from_dict(manifest.to_dict())

    assert restored.cache_validation == validation.to_dict()
    assert restored.cache_validation_status == validation.status
    assert restored.cache_reuse_allowed == validation.reusable


def test_preprocessing_cache_validator_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("models/preprocessing_cache_validation.py"),
        Path("core/preprocessing_cache_validator.py"),
        Path("tests/test_preprocessing_cache_validator_smoke.py"),
        Path("models/preprocessing_manifest.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"
