from __future__ import annotations

import json

from core.job_state_persistence import (
    build_job_state_checkpoint,
    persist_job_state_checkpoint,
)
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


class FakeJobStore:
    def __init__(self) -> None:
        self.updated_jobs = []

    def update_job(self, job):
        self.updated_jobs.append(job)
        return job


def _job(status: JobStatus = JobStatus.CREATED) -> Job:
    job = Job(
        job_id="job_state_persistence_smoke",
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

    job.profile_id = "gaming_main"
    job.quality_mode = "pro"
    job.profile_version = "1.0.0"
    job.profile_snapshot_path = "exports/gaming_main/job_state_persistence_smoke/profile_snapshot.json"
    job.profile_source = "json_profile_manager"

    return job


def test_build_job_state_checkpoint_contains_expected_fields():
    job = _job()

    transition_job_state(
        job,
        JobStatus.ANALYZING,
        module="gaming_pipeline",
        reason="pipeline_analysis_started",
    )

    checkpoint = build_job_state_checkpoint(
        job=job,
        step_name="analyzing",
        reason="pipeline_analysis_started",
    )

    assert checkpoint["job_id"] == "job_state_persistence_smoke"
    assert checkpoint["status"] == "analyzing"
    assert checkpoint["current_module"] == "gaming_pipeline"
    assert checkpoint["step_name"] == "analyzing"
    assert checkpoint["reason"] == "pipeline_analysis_started"

    assert checkpoint["profile_id"] == "gaming_main"
    assert checkpoint["quality_mode"] == "pro"
    assert checkpoint["profile_version"] == "1.0.0"
    assert checkpoint["profile_snapshot_path"].endswith("profile_snapshot.json")
    assert checkpoint["profile_source"] == "json_profile_manager"

    assert checkpoint["state_history_count"] == 1
    assert checkpoint["last_state_transition"]["from"] == "created"
    assert checkpoint["last_state_transition"]["to"] == "analyzing"
    assert checkpoint["timestamp"]

    json.dumps(checkpoint)


def test_persist_job_state_checkpoint_writes_files_and_updates_store(tmp_path):
    job = _job()
    fake_store = FakeJobStore()

    transition_job_state(
        job,
        JobStatus.ANALYZING,
        module="gaming_pipeline",
        reason="pipeline_analysis_started",
    )

    checkpoint = persist_job_state_checkpoint(
        job=job,
        job_store=fake_store,
        export_dir=tmp_path,
        step_name="analyzing",
        reason="pipeline_analysis_started",
    )

    checkpoint_path = tmp_path / "job_state_checkpoint.json"
    jsonl_path = tmp_path / "job_state_checkpoints.jsonl"

    assert checkpoint_path.exists()
    assert jsonl_path.exists()

    loaded_checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert loaded_checkpoint["job_id"] == job.job_id
    assert loaded_checkpoint["status"] == "analyzing"
    assert loaded_checkpoint["state_history_count"] == 1

    jsonl_lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert len(jsonl_lines) == 1
    assert json.loads(jsonl_lines[0])["status"] == "analyzing"

    assert checkpoint["status"] == "analyzing"
    assert fake_store.updated_jobs == [job]


def test_persist_job_state_checkpoint_appends_jsonl(tmp_path):
    job = _job()
    fake_store = FakeJobStore()

    transition_job_state(
        job,
        JobStatus.ANALYZING,
        module="gaming_pipeline",
        reason="pipeline_analysis_started",
    )
    persist_job_state_checkpoint(
        job=job,
        job_store=fake_store,
        export_dir=tmp_path,
        step_name="analyzing",
        reason="pipeline_analysis_started",
    )

    transition_job_state(
        job,
        JobStatus.ANALYZED,
        module="gaming_pipeline",
        reason="analysis_finished",
    )
    persist_job_state_checkpoint(
        job=job,
        job_store=fake_store,
        export_dir=tmp_path,
        step_name="analyzed",
        reason="analysis_finished",
    )

    jsonl_path = tmp_path / "job_state_checkpoints.jsonl"
    jsonl_lines = jsonl_path.read_text(encoding="utf-8").splitlines()

    assert len(jsonl_lines) == 2
    assert json.loads(jsonl_lines[0])["status"] == "analyzing"
    assert json.loads(jsonl_lines[1])["status"] == "analyzed"
    assert fake_store.updated_jobs == [job, job]