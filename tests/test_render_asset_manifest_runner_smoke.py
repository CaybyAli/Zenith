from __future__ import annotations

from core.render_asset_manifest_runner import run_render_asset_manifest_for_job


def _ready_job() -> dict:
    return {
        "job_id": "job_render_asset_runner_smoke",
        "target_platforms": ["youtube"],
        "render_plan_status": "render_plan_ready",
        "render_plan_dry_run_only": True,
        "render_plan_ready_for_renderer_contract": True,
        "render_plan_can_render": False,
        "render_plan_can_run_ffmpeg": False,
        "render_plan_can_write_media": False,
        "render_plan_blocking_reasons": [],
        "render_plan_warnings": [],
        "render_plan_sources": [
            {
                "source_type": "primary_media",
                "path_hint": "inputs/raw/gameplay.mp4",
                "required": True,
            }
        ],
        "render_plan_output_targets": [
            {
                "output_id": "main_youtube",
                "output_type": "planned_video",
                "filename_hint": "runner-output.mp4",
                "directory_hint": "exports/gaming_main/job_render_asset_runner_smoke",
                "container": "mp4",
                "platform": "youtube",
            }
        ],
        "render_plan_report": {
            "status": "render_plan_ready",
            "dry_run_only": True,
            "ready_for_renderer_contract": True,
            "blocking_reasons": [],
            "warnings": [],
        },
        "render_blueprint_status": "render_blueprint_ready",
        "render_blueprint_dry_run_only": True,
        "render_blueprint_non_executable": True,
        "render_blueprint_ready_for_renderer_implementation": True,
        "render_blueprint_can_render": False,
        "render_blueprint_can_run_ffmpeg": False,
        "render_blueprint_can_write_media": False,
        "render_blueprint_blocking_reasons": [],
        "render_blueprint_warnings": [],
        "render_blueprint_steps": [
            {"step_id": "step_censor", "step_type": "censor_sfx"},
            {"step_id": "step_encode", "step_type": "encode"},
        ],
        "render_command_blueprint_report": {
            "status": "render_blueprint_ready",
            "dry_run_only": True,
            "non_executable": True,
            "ready_for_renderer_implementation": True,
            "blocking_reasons": [],
            "warnings": [],
            "blueprint_steps": [
                {"step_id": "step_censor", "step_type": "censor_sfx"},
                {"step_id": "step_encode", "step_type": "encode"},
            ],
        },
    }


def test_runner_writes_render_asset_manifest_fields_to_dict_job():
    job = _ready_job()

    report = run_render_asset_manifest_for_job(job)

    assert job["render_asset_manifest_report"] == report
    assert job["render_asset_manifest"] == report
    assert job["render_asset_manifest_status"] == report["status"]
    assert job["render_asset_references"] == report["asset_references"]
    assert job["render_output_path_plans"] == report["output_path_plans"]

    assert job["render_asset_total_assets"] == report["total_assets"]
    assert job["render_asset_required_count"] == report["required_asset_count"]
    assert job["render_asset_missing_required_hint_count"] == report["missing_required_hint_count"]
    assert job["render_asset_unsafe_path_count"] == report["unsafe_path_count"]
    assert job["render_asset_output_plan_count"] == report["output_plan_count"]

    assert job["render_asset_blocking_reasons"] == report["blocking_reasons"]
    assert job["render_asset_warnings"] == report["warnings"]
    assert job["render_asset_recommendation"] == report["recommendation"]


def test_runner_locks_manifest_safety_flags():
    job = _ready_job()

    run_render_asset_manifest_for_job(job)

    assert job["render_asset_dry_run_only"] is True
    assert job["render_asset_manifest_only"] is True
    assert job["render_asset_paths_are_hints_only"] is True

    assert job["render_asset_can_create_directories"] is False
    assert job["render_asset_can_write_files"] is False
    assert job["render_asset_can_open_media"] is False
    assert job["render_asset_can_render"] is False
    assert job["render_asset_can_run_ffmpeg"] is False


def test_runner_overwrites_dangerous_existing_job_flags():
    job = _ready_job()
    job["render_asset_can_create_directories"] = True
    job["render_asset_can_write_files"] = True
    job["render_asset_can_open_media"] = True
    job["render_asset_can_render"] = True
    job["render_asset_can_run_ffmpeg"] = True

    run_render_asset_manifest_for_job(job)

    assert job["render_asset_can_create_directories"] is False
    assert job["render_asset_can_write_files"] is False
    assert job["render_asset_can_open_media"] is False
    assert job["render_asset_can_render"] is False
    assert job["render_asset_can_run_ffmpeg"] is False


def test_job_from_dict_loads_render_asset_manifest_fields():
    from models.job import Job

    data = {
        "job_id": "job_render_asset_from_dict_smoke",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
        "render_asset_manifest_report": {"status": "render_asset_manifest_ready"},
        "render_asset_manifest": {"status": "render_asset_manifest_ready"},
        "render_asset_manifest_status": "render_asset_manifest_ready",
        "render_asset_references": [{"asset_id": "asset_1"}],
        "render_output_path_plans": [{"output_id": "output_1"}],
        "render_asset_total_assets": 1,
        "render_asset_required_count": 1,
        "render_asset_missing_required_hint_count": 0,
        "render_asset_unsafe_path_count": 0,
        "render_asset_output_plan_count": 1,
        "render_asset_dry_run_only": True,
        "render_asset_manifest_only": True,
        "render_asset_paths_are_hints_only": True,
        "render_asset_can_create_directories": True,
        "render_asset_can_write_files": True,
        "render_asset_can_open_media": True,
        "render_asset_can_render": True,
        "render_asset_can_run_ffmpeg": True,
        "render_asset_blocking_reasons": [],
        "render_asset_warnings": ["hint_only"],
        "render_asset_recommendation": "review_render_asset_manifest",
    }

    job = Job.from_dict(data)

    assert job.render_asset_manifest_report == {"status": "render_asset_manifest_ready"}
    assert job.render_asset_manifest == {"status": "render_asset_manifest_ready"}
    assert job.render_asset_manifest_status == "render_asset_manifest_ready"
    assert job.render_asset_references == [{"asset_id": "asset_1"}]
    assert job.render_output_path_plans == [{"output_id": "output_1"}]
    assert job.render_asset_total_assets == 1
    assert job.render_asset_required_count == 1
    assert job.render_asset_missing_required_hint_count == 0
    assert job.render_asset_unsafe_path_count == 0
    assert job.render_asset_output_plan_count == 1

    assert job.render_asset_dry_run_only is True
    assert job.render_asset_manifest_only is True
    assert job.render_asset_paths_are_hints_only is True

    assert job.render_asset_can_create_directories is False
    assert job.render_asset_can_write_files is False
    assert job.render_asset_can_open_media is False
    assert job.render_asset_can_render is False
    assert job.render_asset_can_run_ffmpeg is False

    assert job.render_asset_warnings == ["hint_only"]
    assert job.render_asset_recommendation == "review_render_asset_manifest"

