from __future__ import annotations

from core.render_execution_permission_gate_runner import (
    run_render_execution_permission_gate_for_job,
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


def _ready_job_dict() -> dict:
    return {
        "job_id": "job_2b49_runner",
        "render_readiness_status": "render_readiness_ready",
        "render_readiness_ready_for_next_render_stage": True,
        "render_readiness_blocking_reasons": [],
        "render_readiness_can_render": False,
        "render_readiness_can_run_ffmpeg": False,
        "render_readiness_can_apply_timeline": False,
        "render_plan_status": "render_plan_ready",
        "render_plan_ready_for_renderer_contract": True,
        "render_plan_blocking_reasons": [],
        "render_plan_can_render": False,
        "render_plan_can_run_ffmpeg": False,
        "render_plan_can_write_media": False,
        "render_plan_can_apply_timeline": False,
        "render_blueprint_status": "render_blueprint_ready",
        "render_blueprint_ready_for_renderer_implementation": True,
        "render_blueprint_non_executable": True,
        "render_blueprint_blocking_reasons": [],
        "render_blueprint_can_render": False,
        "render_blueprint_can_run_ffmpeg": False,
        "render_blueprint_can_spawn_process": False,
        "render_blueprint_can_write_media": False,
        "render_asset_manifest_status": "render_asset_manifest_ready",
        "render_asset_missing_required_hint_count": 0,
        "render_asset_unsafe_path_count": 0,
        "render_asset_blocking_reasons": [],
        "render_asset_can_render": False,
        "render_asset_can_run_ffmpeg": False,
        "render_asset_can_write_files": False,
        "render_asset_can_create_directories": False,
        "render_asset_can_open_media": False,
        "render_execution_human_approved": True,
        "render_execution_requested_status": "approved",
        "render_execution_approved_by": "Hajar",
        "render_execution_approved_at": "2026-05-14T12:00:00+00:00",
        "render_execution_approval_reason": "final manual approval",
    }


def _job_model() -> Job:
    return Job(
        job_id="job_2b49_runner_model",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
    )


def _apply_ready_fields(job: Job) -> Job:
    for key, value in _ready_job_dict().items():
        setattr(job, key, value)
    return job


def test_runner_writes_permission_fields_to_dict_job():
    job = _ready_job_dict()

    report = run_render_execution_permission_gate_for_job(job)

    assert report["status"] == "render_execution_permission_ready"
    assert job["render_execution_permission_status"] == "render_execution_permission_ready"
    assert job["render_execution_permission_report"]["status"] == "render_execution_permission_ready"
    assert job["render_execution_permission_gate"]["status"] == "render_execution_permission_ready"
    assert job["render_execution_permission_total_checks"] == report["total_checks"]
    assert job["render_execution_permission_passed_count"] == report["passed_count"]
    assert job["render_execution_permission_warning_count"] == 0
    assert job["render_execution_permission_blocking_count"] == 0
    assert job["render_execution_permission_review_required"] is False
    assert job["render_execution_ready_for_real_render_stage"] is True
    assert job["render_execution_can_prepare_real_render_execution"] is True
    assert job["render_execution_can_render"] is False
    assert job["render_execution_can_run_ffmpeg"] is False
    assert job["render_execution_can_spawn_process"] is False
    assert job["render_execution_can_write_media"] is False
    assert job["render_execution_can_apply_timeline"] is False
    assert job["render_execution_human_approved"] is True
    assert job["render_execution_approved_by"] == "Hajar"
    assert job["render_execution_blocking_reasons"] == []


def test_runner_writes_permission_fields_to_job_model():
    job = _apply_ready_fields(_job_model())

    report = run_render_execution_permission_gate_for_job(job)

    assert report["status"] == "render_execution_permission_ready"
    assert job.render_execution_permission_status == "render_execution_permission_ready"
    assert job.render_execution_ready_for_real_render_stage is True
    assert job.render_execution_can_prepare_real_render_execution is True
    assert job.render_execution_can_render is False
    assert job.render_execution_can_run_ffmpeg is False
    assert job.render_execution_can_spawn_process is False
    assert job.render_execution_can_write_media is False
    assert job.render_execution_can_apply_timeline is False
    assert job.render_execution_human_approved is True
    assert job.render_execution_approved_by == "Hajar"


def test_runner_blocks_without_human_approval_and_writes_reasons():
    job = _ready_job_dict()
    job["render_execution_human_approved"] = False
    job["render_execution_requested_status"] = None

    report = run_render_execution_permission_gate_for_job(job)

    assert report["status"] == "render_execution_permission_blocked"
    assert job["render_execution_permission_status"] == "render_execution_permission_blocked"
    assert job["render_execution_ready_for_real_render_stage"] is False
    assert job["render_execution_can_prepare_real_render_execution"] is False
    assert "render_execution_human_approval_missing" in job["render_execution_blocking_reasons"]
    assert job["render_execution_can_render"] is False
    assert job["render_execution_can_run_ffmpeg"] is False
    assert job["render_execution_can_spawn_process"] is False
    assert job["render_execution_can_write_media"] is False
    assert job["render_execution_can_apply_timeline"] is False


def test_job_from_dict_loads_render_execution_permission_fields():
    data = _ready_job_dict()
    data.update(
        {
            "job_id": "job_from_dict_2b49",
            "job_type": "gaming",
            "channel_type": "gaming_main",
            "target_format": "short",
            "target_platforms": ["youtube"],
            "status": "routed",
            "mode": "normal",
            "autopublish_class": "manual_only",
            "confidence_score": 0.0,
            "validator_status": "not_validated",
            "render_execution_permission_report": {"status": "loaded"},
            "render_execution_permission_gate": {"status": "loaded"},
            "render_execution_permission_status": "render_execution_permission_ready",
            "render_execution_permission_checks": [{"check_id": "loaded"}],
            "render_execution_permission_total_checks": 15,
            "render_execution_permission_passed_count": 15,
            "render_execution_permission_warning_count": 0,
            "render_execution_permission_blocking_count": 0,
            "render_execution_permission_review_required": False,
            "render_execution_ready_for_real_render_stage": True,
            "render_execution_can_prepare_real_render_execution": True,
            "render_execution_can_render": True,
            "render_execution_can_run_ffmpeg": True,
            "render_execution_can_spawn_process": True,
            "render_execution_can_write_media": True,
            "render_execution_can_apply_timeline": True,
            "render_execution_blocking_reasons": [],
            "render_execution_warnings": [],
            "render_execution_recommendation": "loaded",
        }
    )

    job = Job.from_dict(data)

    assert job.render_execution_permission_report == {"status": "loaded"}
    assert job.render_execution_permission_gate == {"status": "loaded"}
    assert job.render_execution_permission_status == "render_execution_permission_ready"
    assert job.render_execution_permission_checks == [{"check_id": "loaded"}]
    assert job.render_execution_permission_total_checks == 15
    assert job.render_execution_permission_passed_count == 15
    assert job.render_execution_permission_warning_count == 0
    assert job.render_execution_permission_blocking_count == 0
    assert job.render_execution_permission_review_required is False
    assert job.render_execution_ready_for_real_render_stage is True
    assert job.render_execution_can_prepare_real_render_execution is True
    assert job.render_execution_can_render is False
    assert job.render_execution_can_run_ffmpeg is False
    assert job.render_execution_can_spawn_process is False
    assert job.render_execution_can_write_media is False
    assert job.render_execution_can_apply_timeline is False
    assert job.render_execution_human_approved is True
    assert job.render_execution_approved_by == "Hajar"
    assert job.render_execution_recommendation == "loaded"
