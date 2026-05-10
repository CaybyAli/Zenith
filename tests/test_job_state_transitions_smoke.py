from __future__ import annotations

import json

import pytest

from core.job_state_transitions import (
    JobStateTransitionError,
    transition_job_state,
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


def _job(status: JobStatus = JobStatus.CREATED) -> Job:
    return Job(
        job_id="job_state_transition_smoke",
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


def test_valid_pipeline_state_transitions_create_history():
    job = _job()

    transition_job_state(job, JobStatus.ANALYZING, module="gaming_pipeline", reason="analysis_started")
    transition_job_state(job, JobStatus.ANALYZED, module="gaming_pipeline", reason="analysis_finished")
    transition_job_state(job, JobStatus.CUTTING, module="gaming_pipeline", reason="cutting_started")
    transition_job_state(job, JobStatus.CUT, module="gaming_pipeline", reason="cutting_finished")
    transition_job_state(job, JobStatus.RENDERING, module="gaming_pipeline", reason="rendering_started")
    transition_job_state(job, JobStatus.RENDERED, module="gaming_pipeline", reason="rendering_finished")

    assert job.status == JobStatus.RENDERED
    assert job.current_module == "gaming_pipeline"

    assert [entry["to"] for entry in job.state_history] == [
        "analyzing",
        "analyzed",
        "cutting",
        "cut",
        "rendering",
        "rendered",
    ]

    first_entry = job.state_history[0]
    assert first_entry["from"] == "created"
    assert first_entry["to"] == "analyzing"
    assert first_entry["module"] == "gaming_pipeline"
    assert first_entry["reason"] == "analysis_started"
    assert first_entry["timestamp"]


def test_invalid_transition_is_rejected():
    job = _job()

    with pytest.raises(JobStateTransitionError):
        transition_job_state(job, JobStatus.RENDERED, module="test", reason="invalid_direct_jump")

    assert job.status == JobStatus.CREATED
    assert job.state_history == []


def test_failed_transition_is_allowed():
    job = _job()

    transition_job_state(job, JobStatus.ANALYZING, module="gaming_pipeline", reason="analysis_started")
    transition_job_state(job, JobStatus.FAILED, module="gaming_pipeline", reason="analysis_failed")

    assert job.status == JobStatus.FAILED
    assert [entry["to"] for entry in job.state_history] == ["analyzing", "failed"]


def test_same_status_transition_is_noop():
    job = _job(JobStatus.ANALYZING)

    transition_job_state(job, JobStatus.ANALYZING, module="gaming_pipeline", reason="same_status")

    assert job.status == JobStatus.ANALYZING
    assert job.state_history == []


def test_job_to_dict_and_from_dict_preserve_state_history():
    job = _job()

    transition_job_state(job, JobStatus.ANALYZING, module="gaming_pipeline", reason="analysis_started")
    transition_job_state(job, JobStatus.ANALYZED, module="gaming_pipeline", reason="analysis_finished")

    data = job.to_dict()
    json.dumps(data)

    loaded = Job.from_dict(data)

    assert loaded.status == JobStatus.ANALYZED
    assert loaded.state_history == job.state_history
    assert loaded.state_history[0]["from"] == "created"
    assert loaded.state_history[0]["to"] == "analyzing"


def test_rendered_can_move_to_assembled():
    job = _job()

    transition_job_state(job, JobStatus.ANALYZING, module="gaming_pipeline", reason="analysis_started")
    transition_job_state(job, JobStatus.ANALYZED, module="gaming_pipeline", reason="analysis_finished")
    transition_job_state(job, JobStatus.CUTTING, module="gaming_pipeline", reason="cutting_started")
    transition_job_state(job, JobStatus.CUT, module="gaming_pipeline", reason="cutting_finished")
    transition_job_state(job, JobStatus.RENDERING, module="gaming_pipeline", reason="rendering_started")
    transition_job_state(job, JobStatus.RENDERED, module="gaming_pipeline", reason="rendering_finished")
    transition_job_state(job, JobStatus.ASSEMBLED, module="pipeline_runner", reason="export_finished")

    assert job.status == JobStatus.ASSEMBLED
    assert job.state_history[-1]["from"] == "rendered"
    assert job.state_history[-1]["to"] == "assembled"