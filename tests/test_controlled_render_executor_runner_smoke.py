from __future__ import annotations

from core.controlled_render_executor_runner import run_controlled_render_executor_for_job
from models.job import Job


def _ready_job() -> dict:
    return {
        "job_id": "job_2b50_runner",
        "render_execution_permission_report": {"status": "render_execution_permission_ready"},
        "render_execution_permission_status": "render_execution_permission_ready",
        "render_execution_ready_for_real_render_stage": True,
        "render_execution_can_prepare_real_render_execution": True,
        "render_execution_human_approved": True,
        "render_execution_approved_by": "Hajar",
        "render_execution_blocking_reasons": [],
        "render_command_blueprint_report": {"status": "render_blueprint_ready"},
        "render_command_blueprint": {
            "steps": [
                {
                    "step_id": "blueprint_step_1",
                    "step_type": "trim_plan",
                    "description": "Dry-run trim plan.",
                }
            ]
        },
        "render_blueprint_status": "render_blueprint_ready",
        "render_blueprint_steps": [
            {
                "step_id": "blueprint_step_1",
                "step_type": "trim_plan",
                "description": "Dry-run trim plan.",
            }
        ],
        "render_blueprint_non_executable": True,
        "render_blueprint_ready_for_renderer_implementation": True,
        "render_asset_manifest_report": {"status": "render_asset_manifest_ready"},
        "render_asset_manifest_status": "render_asset_manifest_ready",
        "render_asset_can_write_files": False,
        "render_asset_can_open_media": False,
        "render_asset_can_render": False,
        "render_asset_can_run_ffmpeg": False,
    }


def test_runner_writes_controlled_render_job_fields_to_dict_job():
    job = _ready_job()

    report = run_controlled_render_executor_for_job(job)

    assert report["status"] == "controlled_render_executor_dry_run_ready"
    assert job["controlled_render_executor_report"] == report
    assert job["controlled_render_executor"] == report
    assert job["controlled_render_executor_status"] == report["status"]
    assert job["controlled_render_execution_request"]["requested_mode"] == "dry_run"
    assert job["controlled_render_execution_steps"] == report["execution_steps"]
    assert job["controlled_render_total_steps"] == 1
    assert job["controlled_render_planned_step_count"] == 1
    assert job["controlled_render_executed_step_count"] == 0
    assert job["controlled_render_skipped_step_count"] == 1
    assert job["controlled_render_dry_run_only"] is True
    assert job["controlled_render_real_render_requested"] is False
    assert job["controlled_render_real_render_allowed"] is False
    assert job["controlled_render_can_execute_real_render"] is False
    assert job["controlled_render_can_render"] is False
    assert job["controlled_render_can_run_ffmpeg"] is False
    assert job["controlled_render_can_spawn_process"] is False
    assert job["controlled_render_can_write_media"] is False
    assert job["controlled_render_output_created"] is False
    assert job["controlled_render_output_path"] is None
    assert job["controlled_render_blocking_reasons"] == []
    assert job["controlled_render_warnings"] == []


def test_runner_blocks_real_render_request_but_records_request():
    job = _ready_job()
    job["render_execution_requested_mode"] = "real_render"
    job["render_execution_allow_real_render"] = True
    job["render_execution_allow_ffmpeg"] = True
    job["render_execution_allow_process_spawn"] = True
    job["render_execution_allow_media_write"] = True

    report = run_controlled_render_executor_for_job(job)

    assert report["status"] == "controlled_render_executor_blocked"
    assert job["controlled_render_real_render_requested"] is True
    assert job["controlled_render_real_render_allowed"] is False
    assert job["controlled_render_can_execute_real_render"] is False
    assert job["controlled_render_can_render"] is False
    assert job["controlled_render_can_run_ffmpeg"] is False
    assert job["controlled_render_can_spawn_process"] is False
    assert job["controlled_render_can_write_media"] is False
    assert job["controlled_render_output_created"] is False
    assert "real_render_execution_not_implemented_in_2b_50" in job[
        "controlled_render_blocking_reasons"
    ]


def test_job_from_dict_loads_controlled_render_fields_and_forces_safe_false_flags():
    data = {
        "job_id": "job_2b50_from_dict",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube_shorts"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.5,
        "validator_status": "not_validated",
        "render_execution_requested_mode": "real_render",
        "render_execution_allow_real_render": True,
        "render_execution_allow_ffmpeg": True,
        "render_execution_allow_process_spawn": True,
        "render_execution_allow_media_write": True,
        "controlled_render_executor_report": {"status": "controlled_render_executor_blocked"},
        "controlled_render_executor": {"status": "controlled_render_executor_blocked"},
        "controlled_render_executor_status": "controlled_render_executor_blocked",
        "controlled_render_execution_request": {"requested_mode": "real_render"},
        "controlled_render_execution_steps": [{"step_id": "step_1"}],
        "controlled_render_total_steps": 1,
        "controlled_render_planned_step_count": 1,
        "controlled_render_executed_step_count": 99,
        "controlled_render_skipped_step_count": 1,
        "controlled_render_dry_run_only": True,
        "controlled_render_real_render_requested": True,
        "controlled_render_real_render_allowed": True,
        "controlled_render_can_execute_real_render": True,
        "controlled_render_can_render": True,
        "controlled_render_can_run_ffmpeg": True,
        "controlled_render_can_spawn_process": True,
        "controlled_render_can_write_media": True,
        "controlled_render_output_created": True,
        "controlled_render_output_path": "dangerous-output.mp4",
        "controlled_render_blocking_reasons": [
            "real_render_execution_not_implemented_in_2b_50"
        ],
        "controlled_render_warnings": ["manual_review"],
        "controlled_render_recommendation": "review_controlled_render_executor",
    }

    job = Job.from_dict(data)

    assert job.render_execution_requested_mode == "real_render"
    assert job.render_execution_allow_real_render is True
    assert job.render_execution_allow_ffmpeg is True
    assert job.render_execution_allow_process_spawn is True
    assert job.render_execution_allow_media_write is True

    assert job.controlled_render_executor_status == "controlled_render_executor_blocked"
    assert job.controlled_render_execution_request == {"requested_mode": "real_render"}
    assert job.controlled_render_execution_steps == [{"step_id": "step_1"}]
    assert job.controlled_render_total_steps == 1
    assert job.controlled_render_planned_step_count == 1
    assert job.controlled_render_executed_step_count == 99
    assert job.controlled_render_skipped_step_count == 1
    assert job.controlled_render_dry_run_only is True
    assert job.controlled_render_real_render_requested is True

    assert job.controlled_render_real_render_allowed is False
    assert job.controlled_render_can_execute_real_render is False
    assert job.controlled_render_can_render is False
    assert job.controlled_render_can_run_ffmpeg is False
    assert job.controlled_render_can_spawn_process is False
    assert job.controlled_render_can_write_media is False
    assert job.controlled_render_output_created is False
    assert job.controlled_render_output_path is None
