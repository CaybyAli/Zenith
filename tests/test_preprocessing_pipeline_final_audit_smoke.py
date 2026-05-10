from __future__ import annotations

import json
from pathlib import Path

from core.audio_extraction_planner import build_audio_extraction_plan
from core.frame_extraction_planner import build_frame_extraction_plan
from core.preprocessing_cache_validator import validate_preprocessing_cache
from core.preprocessing_manager import (
    build_cache_key,
    build_source_fingerprint,
    prepare_preprocessing_workspace,
)
from core.preprocessing_pipeline import (
    apply_preprocessing_pipeline_report_to_job,
    build_preprocessing_pipeline_report,
)
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


EXPECTED_PREPROCESSING_EVENTS = {
    "PREPROCESSING_WORKSPACE_READY",
    "AUDIO_EXTRACTION_PLAN_READY",
    "FRAME_EXTRACTION_PLAN_READY",
    "PREPROCESSING_CACHE_VALIDATED",
    "PREPROCESSING_READY",
    "PREPROCESSING_FAILED",
}


PREPROCESSING_FIELD_NAMES = [
    "preprocessing_dir",
    "preprocessing_manifest_path",
    "preprocessing_manifest",
    "preprocessing_status",
    "preprocessing_cache_key",
    "preprocessing_reused_cache",
    "audio_extraction_plan",
    "audio_targets",
    "frame_extraction_plan",
    "frame_targets",
    "preprocessing_cache_validation",
    "preprocessing_cache_validation_status",
    "preprocessing_cache_reuse_allowed",
]


def _make_job(raw_video_path: str) -> Job:
    return Job(
        job_id="job_preprocessing_final_audit_001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path=raw_video_path,
    )


def test_preprocessing_workspace_manifest_audio_frame_and_cache_foundation(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "input.mp4"
    source_path.write_text("fake-video", encoding="utf-8")

    fingerprint = build_source_fingerprint(source_path)
    cache_key = build_cache_key(fingerprint)

    assert fingerprint["exists"] is True
    assert fingerprint["size_bytes"] is not None
    assert cache_key

    manifest = prepare_preprocessing_workspace(
        job_id="job_preprocessing_final_audit_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
        metadata={"audit": "2B-05-F"},
    )

    assert isinstance(manifest, PreprocessingManifest)
    assert Path(manifest.preprocessed_dir).exists()
    assert Path(manifest.audio_dir).exists()
    assert Path(manifest.frames_dir).exists()
    assert Path(manifest.thumbnails_dir).exists()
    assert Path(manifest.temp_dir).exists()
    assert Path(manifest.manifest_path).exists()

    restored_manifest = PreprocessingManifest.from_dict(manifest.to_dict())
    assert restored_manifest.cache_key == manifest.cache_key

    audio_plan = build_audio_extraction_plan(manifest)
    frame_plan = build_frame_extraction_plan(manifest)
    cache_validation = validate_preprocessing_cache(manifest)

    assert audio_plan.to_dict()["targets"]
    assert frame_plan.to_dict()["targets"]
    assert isinstance(cache_validation, PreprocessingCacheValidationResult)

    audio_targets = {target.target_id: target for target in audio_plan.targets}
    assert "analysis_audio" in audio_targets
    assert audio_targets["speech_audio"].sample_rate == 16000
    assert audio_targets["speech_audio"].channels == 1
    assert audio_targets["music_reference_audio"].sample_rate == 44100
    assert audio_targets["music_reference_audio"].channels == 2
    assert audio_targets["speech_audio"].command_preview
    assert audio_targets["speech_audio"].command_preview[0] == "ffmpeg"

    frame_targets = {target.target_id: target for target in frame_plan.targets}
    assert "analysis_frames" in frame_targets
    assert "preview_thumbnails" in frame_targets
    assert frame_targets["dense_motion_frames"].enabled is False
    assert frame_targets["analysis_frames"].command_preview
    assert frame_targets["analysis_frames"].command_preview[0] == "ffmpeg"

    assert not Path(manifest.analysis_audio_path).exists()
    assert not Path(manifest.speech_audio_path).exists()
    assert not Path(manifest.music_audio_path).exists()
    assert not list(Path(manifest.frames_dir).glob("*.jpg"))
    assert not list(Path(manifest.thumbnails_dir).glob("*.jpg"))


def test_preprocessing_pipeline_report_contains_all_required_sections(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "input.mp4"
    source_path.write_text("fake-video", encoding="utf-8")

    report = build_preprocessing_pipeline_report(
        job_id="job_preprocessing_final_audit_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
        metadata={"audit": "2B-05-F"},
    )

    required_keys = [
        "preprocessing_manifest",
        "audio_extraction_plan",
        "audio_targets",
        "frame_extraction_plan",
        "frame_targets",
        "cache_validation",
        "preprocessing_dir",
        "manifest_path",
        "status",
        "cache_reuse_allowed",
        "recommendation",
    ]

    for key in required_keys:
        assert key in report

    assert len(report["audio_targets"]) == 3
    assert len(report["frame_targets"]) == 3
    assert report["status"] in ["ready", "ready_with_warnings"]
    assert isinstance(report["cache_reuse_allowed"], bool)
    assert report["recommendation"] in ["continue", "continue_with_review"]


def test_preprocessing_pipeline_manifest_json_contains_plans_and_cache_validation(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "input.mp4"
    source_path.write_text("fake-video", encoding="utf-8")

    report = build_preprocessing_pipeline_report(
        job_id="job_preprocessing_final_audit_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    manifest_path = Path(report["manifest_path"])
    assert manifest_path.exists()

    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert data["audio_extraction_plan"]
    assert len(data["audio_targets"]) == 3
    assert data["frame_extraction_plan"]
    assert len(data["frame_targets"]) == 3
    assert data["cache_validation"]
    assert data["cache_validation_status"]
    assert isinstance(data["cache_reuse_allowed"], bool)


def test_preprocessing_job_roundtrip_preserves_all_pipeline_fields(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "input.mp4"
    source_path.write_text("fake-video", encoding="utf-8")

    report = build_preprocessing_pipeline_report(
        job_id="job_preprocessing_final_audit_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    job = _make_job(raw_video_path=str(source_path))
    apply_preprocessing_pipeline_report_to_job(job, report)

    restored = Job.from_dict(job.to_dict())

    for field_name in PREPROCESSING_FIELD_NAMES:
        assert hasattr(restored, field_name)

    assert restored.preprocessing_dir == job.preprocessing_dir
    assert restored.preprocessing_manifest_path == job.preprocessing_manifest_path
    assert restored.preprocessing_manifest == job.preprocessing_manifest
    assert restored.preprocessing_status == job.preprocessing_status
    assert restored.preprocessing_cache_key == job.preprocessing_cache_key
    assert restored.preprocessing_reused_cache == job.preprocessing_reused_cache
    assert restored.audio_extraction_plan == job.audio_extraction_plan
    assert restored.audio_targets == job.audio_targets
    assert restored.frame_extraction_plan == job.frame_extraction_plan
    assert restored.frame_targets == job.frame_targets
    assert restored.preprocessing_cache_validation == job.preprocessing_cache_validation
    assert (
        restored.preprocessing_cache_validation_status
        == job.preprocessing_cache_validation_status
    )
    assert (
        restored.preprocessing_cache_reuse_allowed
        == job.preprocessing_cache_reuse_allowed
    )


def test_preprocessing_audit_expected_decision_events_are_listed() -> None:
    assert "PREPROCESSING_WORKSPACE_READY" in EXPECTED_PREPROCESSING_EVENTS
    assert "AUDIO_EXTRACTION_PLAN_READY" in EXPECTED_PREPROCESSING_EVENTS
    assert "FRAME_EXTRACTION_PLAN_READY" in EXPECTED_PREPROCESSING_EVENTS
    assert "PREPROCESSING_CACHE_VALIDATED" in EXPECTED_PREPROCESSING_EVENTS
    assert "PREPROCESSING_READY" in EXPECTED_PREPROCESSING_EVENTS
    assert "PREPROCESSING_FAILED" in EXPECTED_PREPROCESSING_EVENTS
    assert len(EXPECTED_PREPROCESSING_EVENTS) == 6


def test_preprocessing_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("models/preprocessing_manifest.py"),
        Path("core/preprocessing_manager.py"),
        Path("models/audio_extraction_plan.py"),
        Path("core/audio_extraction_planner.py"),
        Path("models/frame_extraction_plan.py"),
        Path("core/frame_extraction_planner.py"),
        Path("models/preprocessing_cache_validation.py"),
        Path("core/preprocessing_cache_validator.py"),
        Path("core/preprocessing_pipeline.py"),
        Path("tests/test_preprocessing_manager_smoke.py"),
        Path("tests/test_audio_extraction_planner_smoke.py"),
        Path("tests/test_frame_extraction_planner_smoke.py"),
        Path("tests/test_preprocessing_cache_validator_smoke.py"),
        Path("tests/test_preprocessing_pipeline_integration_smoke.py"),
        Path("tests/test_preprocessing_pipeline_final_audit_smoke.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"
