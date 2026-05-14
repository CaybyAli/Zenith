from __future__ import annotations

from dataclasses import fields

from models.job import Job


BLOCK8_JOB_FIELDS = [
    "render_readiness_guard_report",
    "render_readiness_status",
    "render_readiness_ready_for_next_render_stage",
    "render_readiness_can_start_render_pipeline",
    "render_readiness_can_render",
    "render_readiness_can_run_ffmpeg",
    "render_plan_report",
    "render_plan_status",
    "render_plan_segments",
    "render_plan_dry_run_only",
    "render_plan_ready_for_renderer_contract",
    "render_plan_can_render",
    "render_plan_can_run_ffmpeg",
    "render_plan_can_write_media",
    "render_command_blueprint_report",
    "render_blueprint_status",
    "render_blueprint_steps",
    "render_blueprint_dry_run_only",
    "render_blueprint_non_executable",
    "render_blueprint_can_render",
    "render_blueprint_can_run_ffmpeg",
    "render_asset_manifest_report",
    "render_asset_manifest_status",
    "render_asset_dry_run_only",
    "render_asset_manifest_only",
    "render_asset_paths_are_hints_only",
    "render_asset_can_write_files",
    "render_asset_can_open_media",
    "render_asset_can_render",
    "render_asset_can_run_ffmpeg",
    "render_execution_permission_report",
    "render_execution_permission_status",
    "render_execution_ready_for_real_render_stage",
    "render_execution_can_prepare_real_render_execution",
    "render_execution_can_render",
    "render_execution_can_run_ffmpeg",
    "render_execution_can_spawn_process",
    "render_execution_can_write_media",
    "render_execution_can_apply_timeline",
    "controlled_render_executor_report",
    "controlled_render_executor_status",
    "controlled_render_execution_request",
    "controlled_render_execution_steps",
    "controlled_render_dry_run_only",
    "controlled_render_real_render_allowed",
    "controlled_render_can_execute_real_render",
    "controlled_render_can_render",
    "controlled_render_can_run_ffmpeg",
    "controlled_render_can_spawn_process",
    "controlled_render_can_write_media",
    "controlled_render_output_created",
]

FORCED_FALSE_FIELDS = [
    "render_readiness_can_render",
    "render_readiness_can_run_ffmpeg",
    "render_plan_can_render",
    "render_plan_can_run_ffmpeg",
    "render_plan_can_write_media",
    "render_blueprint_can_render",
    "render_blueprint_can_run_ffmpeg",
    "render_asset_can_write_files",
    "render_asset_can_open_media",
    "render_asset_can_render",
    "render_asset_can_run_ffmpeg",
    "render_execution_can_render",
    "render_execution_can_run_ffmpeg",
    "render_execution_can_spawn_process",
    "render_execution_can_write_media",
    "render_execution_can_apply_timeline",
    "controlled_render_real_render_allowed",
    "controlled_render_can_execute_real_render",
    "controlled_render_can_render",
    "controlled_render_can_run_ffmpeg",
    "controlled_render_can_spawn_process",
    "controlled_render_can_write_media",
    "controlled_render_output_created",
]


def test_job_model_contains_all_block8_fields() -> None:
    field_names = {field.name for field in fields(Job)}
    missing = [name for name in BLOCK8_JOB_FIELDS if name not in field_names]
    assert missing == []


def test_job_from_dict_loads_block8_fields_and_forces_execution_rights_false() -> None:
    data = {
        "job_id": "block8_job_field_audit",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
        "render_readiness_guard_report": {"sentinel": "2b45"},
        "render_readiness_status": "render_readiness_ready",
        "render_readiness_ready_for_next_render_stage": True,
        "render_readiness_can_start_render_pipeline": True,
        "render_plan_report": {"sentinel": "2b46"},
        "render_plan_status": "render_plan_ready",
        "render_plan_segments": [{"segment_id": "seg_1"}],
        "render_plan_dry_run_only": True,
        "render_plan_ready_for_renderer_contract": True,
        "render_command_blueprint_report": {"sentinel": "2b47"},
        "render_blueprint_status": "render_blueprint_ready",
        "render_blueprint_steps": [{"step_id": "bp_1"}],
        "render_blueprint_dry_run_only": True,
        "render_blueprint_non_executable": True,
        "render_asset_manifest_report": {"sentinel": "2b48"},
        "render_asset_manifest_status": "render_asset_manifest_ready",
        "render_asset_dry_run_only": True,
        "render_asset_manifest_only": True,
        "render_asset_paths_are_hints_only": True,
        "render_execution_permission_report": {"sentinel": "2b49"},
        "render_execution_permission_status": "render_execution_permission_ready",
        "render_execution_ready_for_real_render_stage": True,
        "render_execution_can_prepare_real_render_execution": True,
        "controlled_render_executor_report": {"sentinel": "2b50"},
        "controlled_render_executor_status": "controlled_render_executor_dry_run_ready",
        "controlled_render_execution_request": {"requested_mode": "dry_run"},
        "controlled_render_execution_steps": [{"step_id": "controlled_1"}],
        "controlled_render_dry_run_only": True,
    }

    for field_name in FORCED_FALSE_FIELDS:
        data[field_name] = True

    job = Job.from_dict(data)

    assert job.render_readiness_guard_report == {"sentinel": "2b45"}
    assert job.render_plan_report == {"sentinel": "2b46"}
    assert job.render_plan_segments == [{"segment_id": "seg_1"}]
    assert job.render_command_blueprint_report == {"sentinel": "2b47"}
    assert job.render_blueprint_steps == [{"step_id": "bp_1"}]
    assert job.render_asset_manifest_report == {"sentinel": "2b48"}
    assert job.render_execution_permission_report == {"sentinel": "2b49"}
    assert job.controlled_render_executor_report == {"sentinel": "2b50"}
    assert job.controlled_render_execution_request == {"requested_mode": "dry_run"}
    assert job.controlled_render_execution_steps == [{"step_id": "controlled_1"}]

    assert job.render_readiness_ready_for_next_render_stage is True
    assert job.render_plan_dry_run_only is True
    assert job.render_blueprint_non_executable is True
    assert job.render_asset_paths_are_hints_only is True
    assert job.render_execution_ready_for_real_render_stage is True
    assert job.render_execution_can_prepare_real_render_execution is True
    assert job.controlled_render_dry_run_only is True

    leaked = [field_name for field_name in FORCED_FALSE_FIELDS if getattr(job, field_name) is not False]
    assert leaked == []
