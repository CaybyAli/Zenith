from __future__ import annotations

from pathlib import Path

from core.frame_extraction_planner import (
    apply_frame_extraction_plan_to_job,
    apply_frame_extraction_plan_to_manifest,
    build_default_frame_targets,
    build_frame_extraction_plan,
)
from models.frame_extraction_plan import FrameExtractionPlan, FrameExtractionTarget
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


def _make_manifest(status: str = "ready") -> PreprocessingManifest:
    return PreprocessingManifest(
        job_id="job_frame_001",
        source_path="input.mp4",
        source_fingerprint={
            "path": "input.mp4",
            "exists": status != "missing_source",
            "size_bytes": 123,
            "mtime_ns": 456,
        },
        cache_key="cache123",
        preprocessed_dir="preprocessed/job_frame_001",
        audio_dir="preprocessed/job_frame_001/audio",
        frames_dir="preprocessed/job_frame_001/frames",
        thumbnails_dir="preprocessed/job_frame_001/thumbnails",
        temp_dir="preprocessed/job_frame_001/temp",
        manifest_path="preprocessed/job_frame_001/manifest.json",
        analysis_audio_path="preprocessed/job_frame_001/audio/analysis.wav",
        speech_audio_path="preprocessed/job_frame_001/audio/speech_16k_mono.wav",
        music_audio_path="preprocessed/job_frame_001/audio/music_reference.wav",
        frame_pattern="preprocessed/job_frame_001/frames/frame_%06d.jpg",
        thumbnail_pattern="preprocessed/job_frame_001/thumbnails/thumb_%06d.jpg",
        status=status,
        reused_cache=False,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        warnings=[],
        errors=["source_missing"] if status == "missing_source" else [],
        metadata={"test": True},
    )


def _make_job() -> Job:
    return Job(
        job_id="job_frame_001",
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


def test_frame_extraction_target_roundtrip() -> None:
    target = FrameExtractionTarget(
        target_id="preview_thumbnails",
        purpose="preview_thumbnail",
        output_pattern="preprocessed/job/thumbnails/thumb_%06d.jpg",
        format="jpg",
        interval_seconds=10.0,
        width=640,
        height=None,
        fps=None,
        enabled=True,
        status="planned",
        command_preview=[
            "ffmpeg",
            "-i",
            "input.mp4",
            "-vf",
            "fps=1/10.0,scale=640:-1",
            "preprocessed/job/thumbnails/thumb_%06d.jpg",
        ],
        warnings=[],
        errors=[],
        metadata={"kind": "thumbnail"},
    )

    restored = FrameExtractionTarget.from_dict(target.to_dict())

    assert restored.target_id == target.target_id
    assert restored.purpose == target.purpose
    assert restored.output_pattern == target.output_pattern
    assert restored.format == target.format
    assert restored.interval_seconds == target.interval_seconds
    assert restored.width == target.width
    assert restored.height == target.height
    assert restored.fps == target.fps
    assert restored.enabled == target.enabled
    assert restored.status == target.status
    assert restored.command_preview == target.command_preview
    assert restored.warnings == target.warnings
    assert restored.errors == target.errors
    assert restored.metadata == target.metadata


def test_frame_extraction_plan_roundtrip() -> None:
    target = FrameExtractionTarget(
        target_id="analysis_frames",
        purpose="analysis",
        output_pattern="preprocessed/job/frames/frame_%06d.jpg",
        interval_seconds=1.0,
    )
    plan = FrameExtractionPlan(
        job_id="job_frame_001",
        source_path="input.mp4",
        frames_dir="preprocessed/job_frame_001/frames",
        thumbnails_dir="preprocessed/job_frame_001/thumbnails",
        targets=[target],
        status="planned",
        warnings=[],
        errors=[],
        metadata={"channel": "gaming_main"},
    )

    restored = FrameExtractionPlan.from_dict(plan.to_dict())

    assert restored.job_id == plan.job_id
    assert restored.source_path == plan.source_path
    assert restored.frames_dir == plan.frames_dir
    assert restored.thumbnails_dir == plan.thumbnails_dir
    assert len(restored.targets) == 1
    assert restored.targets[0].target_id == "analysis_frames"
    assert restored.status == plan.status
    assert restored.warnings == plan.warnings
    assert restored.errors == plan.errors
    assert restored.metadata == plan.metadata


def test_build_default_frame_targets() -> None:
    manifest = _make_manifest()

    targets = build_default_frame_targets(manifest)

    assert len(targets) == 3
    assert [target.target_id for target in targets] == [
        "analysis_frames",
        "preview_thumbnails",
        "dense_motion_frames",
    ]


def test_analysis_frames_target_is_one_second_interval() -> None:
    manifest = _make_manifest()

    targets = build_default_frame_targets(manifest)
    analysis_target = next(target for target in targets if target.target_id == "analysis_frames")

    assert analysis_target.purpose == "analysis"
    assert analysis_target.interval_seconds == 1.0
    assert analysis_target.output_pattern.endswith("frame_%06d.jpg")


def test_preview_thumbnail_target_is_ten_second_interval_and_scaled() -> None:
    manifest = _make_manifest()

    targets = build_default_frame_targets(manifest)
    preview_target = next(target for target in targets if target.target_id == "preview_thumbnails")

    assert preview_target.purpose == "preview_thumbnail"
    assert preview_target.interval_seconds == 10.0
    assert preview_target.width == 640
    assert preview_target.output_pattern.endswith("thumb_%06d.jpg")
    assert any("scale=640:-1" in part for part in preview_target.command_preview)


def test_dense_motion_frames_are_disabled_by_default() -> None:
    manifest = _make_manifest()

    targets = build_default_frame_targets(manifest)
    motion_target = next(target for target in targets if target.target_id == "dense_motion_frames")

    assert motion_target.purpose == "motion_analysis"
    assert motion_target.enabled is False
    assert motion_target.status == "planned_disabled"
    assert "disabled_by_default" in motion_target.warnings
    assert motion_target.output_pattern.endswith("motion_%06d.jpg")


def test_command_preview_is_built_but_not_executed(tmp_path: Path) -> None:
    manifest = _make_manifest()
    manifest.source_path = str(tmp_path / "input.mp4")
    manifest.frame_pattern = str(tmp_path / "frames" / "frame_%06d.jpg")

    targets = build_default_frame_targets(manifest)
    analysis_target = next(target for target in targets if target.target_id == "analysis_frames")

    assert analysis_target.command_preview[0] == "ffmpeg"
    assert "-i" in analysis_target.command_preview
    assert manifest.source_path in analysis_target.command_preview
    assert manifest.frame_pattern in analysis_target.command_preview
    assert not Path(manifest.frame_pattern).exists()


def test_build_frame_extraction_plan_blocks_missing_source() -> None:
    manifest = _make_manifest(status="missing_source")

    plan = build_frame_extraction_plan(manifest)

    assert plan.status == "blocked"
    assert "source_missing" in plan.errors


def test_apply_frame_extraction_plan_to_manifest_sets_fields() -> None:
    manifest = _make_manifest()
    plan = build_frame_extraction_plan(manifest)

    apply_frame_extraction_plan_to_manifest(manifest, plan)

    assert manifest.frame_extraction_plan == plan.to_dict()
    assert len(manifest.frame_targets) == 3
    assert manifest.frame_targets[0]["target_id"] == "analysis_frames"


def test_apply_frame_extraction_plan_to_job_sets_fields() -> None:
    manifest = _make_manifest()
    plan = build_frame_extraction_plan(manifest)
    job = _make_job()

    apply_frame_extraction_plan_to_job(job, plan)

    assert job.frame_extraction_plan == plan.to_dict()
    assert len(job.frame_targets) == 3
    assert job.frame_targets[1]["target_id"] == "preview_thumbnails"


def test_job_to_dict_from_dict_preserves_frame_extraction_fields() -> None:
    manifest = _make_manifest()
    plan = build_frame_extraction_plan(manifest)
    job = _make_job()

    apply_frame_extraction_plan_to_job(job, plan)

    restored = Job.from_dict(job.to_dict())

    assert restored.frame_extraction_plan == plan.to_dict()
    assert restored.frame_targets == plan.to_dict()["targets"]


def test_preprocessing_manifest_roundtrip_preserves_frame_fields() -> None:
    manifest = _make_manifest()
    plan = build_frame_extraction_plan(manifest)

    apply_frame_extraction_plan_to_manifest(manifest, plan)
    restored = PreprocessingManifest.from_dict(manifest.to_dict())

    assert restored.frame_extraction_plan == plan.to_dict()
    assert restored.frame_targets == plan.to_dict()["targets"]


def test_frame_extraction_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("models/frame_extraction_plan.py"),
        Path("core/frame_extraction_planner.py"),
        Path("tests/test_frame_extraction_planner_smoke.py"),
        Path("models/preprocessing_manifest.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"
