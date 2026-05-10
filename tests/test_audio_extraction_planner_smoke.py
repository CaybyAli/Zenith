from __future__ import annotations

from pathlib import Path

from core.audio_extraction_planner import (
    apply_audio_extraction_plan_to_job,
    apply_audio_extraction_plan_to_manifest,
    build_audio_extraction_plan,
    build_default_audio_targets,
)
from models.audio_extraction_plan import AudioExtractionPlan, AudioExtractionTarget
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
        job_id="job_audio_001",
        source_path="input.mp4",
        source_fingerprint={
            "path": "input.mp4",
            "exists": status != "missing_source",
            "size_bytes": 123,
            "mtime_ns": 456,
        },
        cache_key="cache123",
        preprocessed_dir="preprocessed/job_audio_001",
        audio_dir="preprocessed/job_audio_001/audio",
        frames_dir="preprocessed/job_audio_001/frames",
        thumbnails_dir="preprocessed/job_audio_001/thumbnails",
        temp_dir="preprocessed/job_audio_001/temp",
        manifest_path="preprocessed/job_audio_001/manifest.json",
        analysis_audio_path="preprocessed/job_audio_001/audio/analysis.wav",
        speech_audio_path="preprocessed/job_audio_001/audio/speech_16k_mono.wav",
        music_audio_path="preprocessed/job_audio_001/audio/music_reference.wav",
        frame_pattern="preprocessed/job_audio_001/frames/frame_%06d.jpg",
        thumbnail_pattern="preprocessed/job_audio_001/thumbnails/thumb_%06d.jpg",
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
        job_id="job_audio_001",
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


def test_audio_extraction_target_roundtrip() -> None:
    target = AudioExtractionTarget(
        target_id="speech_audio",
        purpose="speech",
        output_path="preprocessed/job/audio/speech_16k_mono.wav",
        format="wav",
        sample_rate=16000,
        channels=1,
        source_stream_index=1,
        enabled=True,
        status="planned",
        command_preview=[
            "ffmpeg",
            "-i",
            "input.mp4",
            "-vn",
            "-map",
            "0:1",
            "-ac",
            "1",
            "-ar",
            "16000",
            "preprocessed/job/audio/speech_16k_mono.wav",
        ],
        warnings=[],
        errors=[],
        metadata={"kind": "speech"},
    )

    restored = AudioExtractionTarget.from_dict(target.to_dict())

    assert restored.target_id == target.target_id
    assert restored.purpose == target.purpose
    assert restored.output_path == target.output_path
    assert restored.format == target.format
    assert restored.sample_rate == target.sample_rate
    assert restored.channels == target.channels
    assert restored.source_stream_index == target.source_stream_index
    assert restored.enabled == target.enabled
    assert restored.status == target.status
    assert restored.command_preview == target.command_preview
    assert restored.warnings == target.warnings
    assert restored.errors == target.errors
    assert restored.metadata == target.metadata


def test_audio_extraction_plan_roundtrip() -> None:
    target = AudioExtractionTarget(
        target_id="analysis_audio",
        purpose="analysis",
        output_path="preprocessed/job/audio/analysis.wav",
        sample_rate=44100,
        channels=2,
    )
    plan = AudioExtractionPlan(
        job_id="job_audio_001",
        source_path="input.mp4",
        audio_dir="preprocessed/job_audio_001/audio",
        targets=[target],
        status="planned",
        warnings=[],
        errors=[],
        metadata={"channel": "gaming_main"},
    )

    restored = AudioExtractionPlan.from_dict(plan.to_dict())

    assert restored.job_id == plan.job_id
    assert restored.source_path == plan.source_path
    assert restored.audio_dir == plan.audio_dir
    assert len(restored.targets) == 1
    assert restored.targets[0].target_id == "analysis_audio"
    assert restored.status == plan.status
    assert restored.warnings == plan.warnings
    assert restored.errors == plan.errors
    assert restored.metadata == plan.metadata


def test_build_default_audio_targets() -> None:
    manifest = _make_manifest()

    targets = build_default_audio_targets(manifest)

    assert len(targets) == 3
    assert [target.target_id for target in targets] == [
        "analysis_audio",
        "speech_audio",
        "music_reference_audio",
    ]


def test_speech_audio_is_16k_mono() -> None:
    manifest = _make_manifest()

    targets = build_default_audio_targets(manifest)
    speech_target = next(target for target in targets if target.target_id == "speech_audio")

    assert speech_target.purpose == "speech"
    assert speech_target.sample_rate == 16000
    assert speech_target.channels == 1
    assert speech_target.output_path.endswith("speech_16k_mono.wav")


def test_analysis_and_music_audio_are_44100_stereo() -> None:
    manifest = _make_manifest()

    targets = build_default_audio_targets(manifest)
    analysis_target = next(target for target in targets if target.target_id == "analysis_audio")
    music_target = next(
        target for target in targets if target.target_id == "music_reference_audio"
    )

    assert analysis_target.sample_rate == 44100
    assert analysis_target.channels == 2
    assert music_target.sample_rate == 44100
    assert music_target.channels == 2


def test_command_preview_is_built_but_not_executed(tmp_path: Path) -> None:
    manifest = _make_manifest()
    manifest.source_path = str(tmp_path / "input.mp4")
    manifest.speech_audio_path = str(tmp_path / "speech_16k_mono.wav")

    targets = build_default_audio_targets(manifest)
    speech_target = next(target for target in targets if target.target_id == "speech_audio")

    assert speech_target.command_preview[0] == "ffmpeg"
    assert "-i" in speech_target.command_preview
    assert manifest.source_path in speech_target.command_preview
    assert manifest.speech_audio_path in speech_target.command_preview
    assert not Path(manifest.speech_audio_path).exists()


def test_build_audio_extraction_plan_blocks_missing_source() -> None:
    manifest = _make_manifest(status="missing_source")

    plan = build_audio_extraction_plan(manifest)

    assert plan.status == "blocked"
    assert "source_missing" in plan.errors


def test_apply_audio_extraction_plan_to_manifest_sets_fields() -> None:
    manifest = _make_manifest()
    plan = build_audio_extraction_plan(manifest)

    apply_audio_extraction_plan_to_manifest(manifest, plan)

    assert manifest.audio_extraction_plan == plan.to_dict()
    assert len(manifest.audio_targets) == 3
    assert manifest.audio_targets[0]["target_id"] == "analysis_audio"


def test_apply_audio_extraction_plan_to_job_sets_fields() -> None:
    manifest = _make_manifest()
    plan = build_audio_extraction_plan(manifest)
    job = _make_job()

    apply_audio_extraction_plan_to_job(job, plan)

    assert job.audio_extraction_plan == plan.to_dict()
    assert len(job.audio_targets) == 3
    assert job.audio_targets[1]["target_id"] == "speech_audio"


def test_job_to_dict_from_dict_preserves_audio_extraction_fields() -> None:
    manifest = _make_manifest()
    plan = build_audio_extraction_plan(manifest)
    job = _make_job()

    apply_audio_extraction_plan_to_job(job, plan)

    restored = Job.from_dict(job.to_dict())

    assert restored.audio_extraction_plan == plan.to_dict()
    assert restored.audio_targets == plan.to_dict()["targets"]


def test_preprocessing_manifest_roundtrip_preserves_audio_fields() -> None:
    manifest = _make_manifest()
    plan = build_audio_extraction_plan(manifest)

    apply_audio_extraction_plan_to_manifest(manifest, plan)
    restored = PreprocessingManifest.from_dict(manifest.to_dict())

    assert restored.audio_extraction_plan == plan.to_dict()
    assert restored.audio_targets == plan.to_dict()["targets"]


def test_audio_extraction_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("models/audio_extraction_plan.py"),
        Path("core/audio_extraction_planner.py"),
        Path("tests/test_audio_extraction_planner_smoke.py"),
        Path("models/preprocessing_manifest.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"
