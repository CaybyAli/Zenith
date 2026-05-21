from __future__ import annotations

from pathlib import Path

from core import existing_longform_shorts_stage as stage
from models.job import Job
from models.shorts_clip import ShortsClip
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


def _job(job_id: str) -> Job:
    return Job(
        job_id=job_id,
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.BOTH,
        target_platforms=["youtube"],
        status=JobStatus.RENDERED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
    )


def test_detects_existing_longform_output_when_job_json_is_present(tmp_path: Path) -> None:
    output = tmp_path / "job_demo_v1_final.mp4"
    output.write_bytes(b"fake mp4")
    (tmp_path / "job.json").write_text("{}", encoding="utf-8")

    assert stage.is_existing_longform_output_path(output) is True


def test_rejects_existing_longform_output_without_job_json(tmp_path: Path) -> None:
    output = tmp_path / "job_demo_v1_final.mp4"
    output.write_bytes(b"fake mp4")

    assert stage.is_existing_longform_output_path(output) is False


def test_build_existing_longform_timeline_has_enough_non_overlapping_windows() -> None:
    job = _job("job_existing_longform_test")

    timeline = stage.build_existing_longform_shorts_timeline(
        job,
        duration_seconds=736.0,
    )

    assert len(timeline.selected_segments) >= 5
    assert all(
        segment.end_time - segment.start_time <= 60.0
        for segment in timeline.selected_segments
    )
    assert all(
        left.end_time <= right.start_time
        for left, right in zip(
            timeline.selected_segments,
            timeline.selected_segments[1:],
        )
    )


def test_run_existing_longform_uses_stage_and_sets_shorts(monkeypatch, tmp_path: Path) -> None:
    job = _job("job_existing_longform_run_test")
    source = tmp_path / "job_existing_v1_final.mp4"
    source.write_bytes(b"fake mp4")
    (tmp_path / "job.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(stage, "_probe_duration_seconds", lambda path: 736.0)

    class FakeShortsGenerationStage:
        def run(
            self,
            job,
            timeline,
            source_video_path,
            output_base_dir,
            power_profile="balanced",
            llm_mode="LLM_SHADOW",
            add_captions=True,
        ):
            target_count = 5 if str(power_profile) == "performance" else 3
            job.shorts_clips = [
                ShortsClip(
                    source_job_id=job.job_id,
                    source_start_time=float(index * 60),
                    source_end_time=float(index * 60 + 60),
                    planned_duration=60.0,
                    hook_score=1.0 - index * 0.01,
                    clip_index=index,
                    status="rendered",
                    output_path=str(Path(output_base_dir) / f"short_{index}.mp4"),
                )
                for index in range(target_count)
            ]
            job.status = JobStatus.SHORTS_RENDERED
            return job

    monkeypatch.setattr(stage, "ShortsGenerationStage", FakeShortsGenerationStage)

    result = stage.run_shorts_from_existing_longform_output(
        job=job,
        source_video_path=source,
        output_base_dir=tmp_path / "exports",
        power_profile="performance",
    )

    assert result["shorts_from_existing_longform"] is True
    assert result["shorts_count"] == 5
    assert job.status == JobStatus.SHORTS_RENDERED
