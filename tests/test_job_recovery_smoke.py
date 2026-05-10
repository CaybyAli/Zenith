from __future__ import annotations

import json

from core.job_recovery import (
    apply_recovery_report_to_job,
    build_recovery_report,
)
from core.job_state_persistence import persist_job_state_checkpoint
from core.job_state_transitions import transition_job_state
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


def _job(status: JobStatus = JobStatus.CREATED) -> Job:
    return Job(
        job_id="job_recovery_smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=status,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/test.mp4",
    )


def test_assembled_job_is_clean_complete_reviewable(tmp_path):
    job = _job(JobStatus.RENDERED)

    transition_job_state(
        job,
        JobStatus.ASSEMBLED,
        module="pipeline_runner",
        reason="export_finished",
    )
    persist_job_state_checkpoint(
        job=job,
        export_dir=tmp_path,
        step_name="assembled",
        reason="export_finished",
    )

    report = build_recovery_report(job, export_dir=tmp_path)

    assert report["recovery_status"] == "clean_complete"
    assert report["resume_safety"] == "safe"
    assert report["recommended_action"] == "review_or_publish"
    assert report["checkpoint_count"] == 1
    assert report["state_history_count"] == 1
    assert report["last_checkpoint_path"].endswith("job_state_checkpoint.json")

    json.dumps(report)


def test_analyzing_job_with_checkpoint_needs_recovery_caution(tmp_path):
    job = _job()

    transition_job_state(
        job,
        JobStatus.ANALYZING,
        module="gaming_pipeline",
        reason="pipeline_analysis_started",
    )
    persist_job_state_checkpoint(
        job=job,
        export_dir=tmp_path,
        step_name="analyzing",
        reason="pipeline_analysis_started",
    )

    report = build_recovery_report(job, export_dir=tmp_path)

    assert report["recovery_status"] == "needs_recovery"
    assert report["resume_safety"] == "caution"
    assert report["recommended_action"] == "manual_review"
    assert report["reason"] == "job_interrupted_during_analyzing"


def test_rendering_job_with_checkpoint_needs_recovery_unsafe(tmp_path):
    job = _job()

    transition_job_state(job, JobStatus.ANALYZING, module="gaming_pipeline")
    transition_job_state(job, JobStatus.ANALYZED, module="gaming_pipeline")
    transition_job_state(job, JobStatus.CUTTING, module="gaming_pipeline")
    transition_job_state(job, JobStatus.CUT, module="gaming_pipeline")
    transition_job_state(
        job,
        JobStatus.RENDERING,
        module="gaming_pipeline",
        reason="rendering_started",
    )
    persist_job_state_checkpoint(
        job=job,
        export_dir=tmp_path,
        step_name="rendering",
        reason="rendering_started",
    )

    report = build_recovery_report(job, export_dir=tmp_path)

    assert report["recovery_status"] == "needs_recovery"
    assert report["resume_safety"] == "unsafe"
    assert report["recommended_action"] == "manual_review"
    assert report["reason"] == "job_interrupted_during_rendering"


def test_failed_job_requires_manual_review():
    job = _job(JobStatus.FAILED)
    job.error_message = "boom"

    report = build_recovery_report(job)

    assert report["recovery_status"] == "manual_review_required"
    assert report["resume_safety"] == "unsafe"
    assert report["recommended_action"] == "inspect_error"
    assert report["reason"] == "job_failed"


def test_missing_checkpoint_does_not_crash(tmp_path):
    job = _job(JobStatus.ANALYZING)

    report = build_recovery_report(job, export_dir=tmp_path)

    assert report["recovery_status"] == "unknown"
    assert report["resume_safety"] == "unknown"
    assert report["recommended_action"] == "manual_review"
    assert report["last_checkpoint_path"] is None
    assert report["last_checkpoint"] is None
    assert report["checkpoint_count"] == 0


def test_apply_recovery_report_to_job_sets_fields(tmp_path):
    job = _job(JobStatus.RENDERED)

    transition_job_state(
        job,
        JobStatus.ASSEMBLED,
        module="pipeline_runner",
        reason="export_finished",
    )
    persist_job_state_checkpoint(
        job=job,
        export_dir=tmp_path,
        step_name="assembled",
        reason="export_finished",
    )

    report = build_recovery_report(job, export_dir=tmp_path)
    apply_recovery_report_to_job(job, report)

    assert job.recovery_status == "clean_complete"
    assert job.resume_safety == "safe"
    assert job.recovery_report["recommended_action"] == "review_or_publish"


def test_job_to_dict_from_dict_keeps_recovery_fields(tmp_path):
    job = _job(JobStatus.RENDERED)

    transition_job_state(
        job,
        JobStatus.ASSEMBLED,
        module="pipeline_runner",
        reason="export_finished",
    )
    persist_job_state_checkpoint(
        job=job,
        export_dir=tmp_path,
        step_name="assembled",
        reason="export_finished",
    )

    report = build_recovery_report(job, export_dir=tmp_path)
    apply_recovery_report_to_job(job, report)

    loaded = Job.from_dict(job.to_dict())

    assert loaded.recovery_status == "clean_complete"
    assert loaded.resume_safety == "safe"
    assert loaded.recovery_report["recovery_status"] == "clean_complete"
    assert loaded.recovery_report["resume_safety"] == "safe"