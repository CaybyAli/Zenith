from __future__ import annotations

import json
from pathlib import Path

from core.preprocessing_pipeline import (
    apply_preprocessing_pipeline_report_to_job,
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


def _make_job(raw_video_path: str = "input.mp4") -> Job:
    return Job(
        job_id="job_preprocessing_pipeline_001",
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


def test_preprocessing_pipeline_report_builds_all_sections(tmp_path: Path) -> None:
    source_path = tmp_path / "input.mp4"
    source_path.write_text("fake-video", encoding="utf-8")

    report = build_preprocessing_pipeline_report(
        job_id="job_preprocessing_pipeline_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
        metadata={"test": True},
    )

    assert report["preprocessing_manifest"]
    assert report["audio_extraction_plan"]
    assert report["frame_extraction_plan"]
    assert report["cache_validation"]
    assert len(report["audio_targets"]) == 3
    assert len(report["frame_targets"]) == 3
    assert report["status"] in ["ready", "ready_with_warnings"]


def test_preprocessing_pipeline_creates_manifest_file(tmp_path: Path) -> None:
    source_path = tmp_path / "input.mp4"
    source_path.write_text("fake-video", encoding="utf-8")

    report = build_preprocessing_pipeline_report(
        job_id="job_preprocessing_pipeline_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    manifest_path = Path(report["manifest_path"])

    assert manifest_path.exists()

    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert data["audio_extraction_plan"]
    assert data["frame_extraction_plan"]
    assert data["cache_validation"]


def test_apply_preprocessing_pipeline_report_to_job_sets_fields(tmp_path: Path) -> None:
    source_path = tmp_path / "input.mp4"
    source_path.write_text("fake-video", encoding="utf-8")

    report = build_preprocessing_pipeline_report(
        job_id="job_preprocessing_pipeline_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )
    job = _make_job(raw_video_path=str(source_path))

    apply_preprocessing_pipeline_report_to_job(job, report)

    assert job.preprocessing_dir == report["preprocessing_dir"]
    assert job.preprocessing_manifest_path == report["manifest_path"]
    assert job.preprocessing_manifest == report["preprocessing_manifest"]
    assert job.preprocessing_status == report["status"]
    assert job.preprocessing_cache_key
    assert job.audio_extraction_plan == report["audio_extraction_plan"]
    assert job.audio_targets == report["audio_targets"]
    assert job.frame_extraction_plan == report["frame_extraction_plan"]
    assert job.frame_targets == report["frame_targets"]
    assert job.preprocessing_cache_validation == report["cache_validation"]


def test_run_preprocessing_pipeline_for_job_sets_job_fields(tmp_path: Path) -> None:
    source_path = tmp_path / "input.mp4"
    source_path.write_text("fake-video", encoding="utf-8")
    job = _make_job(raw_video_path=str(source_path))

    report = run_preprocessing_pipeline_for_job(
        job=job,
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
        metadata={"test": True},
    )

    assert job.preprocessing_dir == report["preprocessing_dir"]
    assert job.preprocessing_manifest_path == report["manifest_path"]
    assert job.audio_extraction_plan == report["audio_extraction_plan"]
    assert job.frame_extraction_plan == report["frame_extraction_plan"]
    assert job.preprocessing_cache_validation == report["cache_validation"]


def test_job_to_dict_from_dict_preserves_preprocessing_pipeline_fields(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "input.mp4"
    source_path.write_text("fake-video", encoding="utf-8")
    job = _make_job(raw_video_path=str(source_path))

    report = run_preprocessing_pipeline_for_job(
        job=job,
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    restored = Job.from_dict(job.to_dict())

    assert restored.preprocessing_dir == report["preprocessing_dir"]
    assert restored.preprocessing_manifest_path == report["manifest_path"]
    assert restored.preprocessing_manifest == report["preprocessing_manifest"]
    assert restored.audio_extraction_plan == report["audio_extraction_plan"]
    assert restored.audio_targets == report["audio_targets"]
    assert restored.frame_extraction_plan == report["frame_extraction_plan"]
    assert restored.frame_targets == report["frame_targets"]
    assert restored.preprocessing_cache_validation == report["cache_validation"]
    assert (
        restored.preprocessing_cache_reuse_allowed
        == report["cache_reuse_allowed"]
    )


def test_missing_source_report_is_failed(tmp_path: Path) -> None:
    source_path = tmp_path / "missing.mp4"

    report = build_preprocessing_pipeline_report(
        job_id="job_preprocessing_pipeline_001",
        source_path=source_path,
        root_dir=tmp_path / "preprocessed",
    )

    assert report["status"] == "failed"
    assert "source_missing" in report["errors"]
    assert report["recommendation"] == "fix_or_rebuild"


def test_preprocessing_pipeline_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("core/preprocessing_pipeline.py"),
        Path("tests/test_preprocessing_pipeline_integration_smoke.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"
