from __future__ import annotations

from core.controlled_render_executor import build_controlled_render_executor


def _ready_job() -> dict:
    return {
        "job_id": "job_2b50_smoke",
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
                    "description": "Would trim source in a future real renderer.",
                },
                {
                    "step_id": "blueprint_step_2",
                    "step_type": "encode_plan",
                    "description": "Would encode output in a future real renderer.",
                },
            ]
        },
        "render_blueprint_status": "render_blueprint_ready",
        "render_blueprint_steps": [
            {
                "step_id": "blueprint_step_1",
                "step_type": "trim_plan",
                "description": "Would trim source in a future real renderer.",
            },
            {
                "step_id": "blueprint_step_2",
                "step_type": "encode_plan",
                "description": "Would encode output in a future real renderer.",
            },
        ],
        "render_blueprint_non_executable": True,
        "render_blueprint_ready_for_renderer_implementation": True,
        "render_asset_manifest_report": {"status": "render_asset_manifest_ready"},
        "render_asset_manifest_status": "render_asset_manifest_ready",
        "render_asset_can_write_files": False,
        "render_asset_can_open_media": False,
        "render_asset_can_render": False,
        "render_asset_can_run_ffmpeg": False,
        "render_execution_requested_mode": "dry_run",
        "render_execution_allow_real_render": False,
        "render_execution_allow_ffmpeg": False,
        "render_execution_allow_process_spawn": False,
        "render_execution_allow_media_write": False,
    }


def _blocked_with(job: dict, expected_reason: str) -> dict:
    report = build_controlled_render_executor(job)

    assert report["status"] == "controlled_render_executor_blocked"
    assert expected_reason in report["blocking_reasons"]
    assert report["dry_run_only"] is True
    assert report["real_render_allowed"] is False
    assert report["can_execute_real_render"] is False
    assert report["can_render"] is False
    assert report["can_run_ffmpeg"] is False
    assert report["can_spawn_process"] is False
    assert report["can_write_media"] is False
    assert report["output_created"] is False
    assert report["output_path"] is None
    return report


def test_executor_blocks_when_permission_gate_missing():
    job = _ready_job()
    job["render_execution_permission_report"] = {}

    _blocked_with(job, "render_execution_permission_gate_missing")


def test_executor_blocks_when_permission_gate_not_ready():
    job = _ready_job()
    job["render_execution_permission_status"] = "render_execution_permission_blocked"

    _blocked_with(job, "render_execution_permission_gate_not_ready")


def test_executor_blocks_when_ready_for_real_render_stage_false():
    job = _ready_job()
    job["render_execution_ready_for_real_render_stage"] = False

    _blocked_with(job, "render_execution_stage_not_ready")


def test_executor_blocks_when_can_prepare_real_render_execution_false():
    job = _ready_job()
    job["render_execution_can_prepare_real_render_execution"] = False

    _blocked_with(job, "render_execution_prepare_not_allowed")


def test_executor_blocks_when_human_approval_missing():
    job = _ready_job()
    job["render_execution_human_approved"] = False

    _blocked_with(job, "render_execution_human_approval_missing")


def test_executor_blocks_on_permission_gate_blocking_reasons():
    job = _ready_job()
    job["render_execution_blocking_reasons"] = ["manual_gate_block"]

    _blocked_with(job, "permission_gate:manual_gate_block")


def test_executor_blocks_when_blueprint_missing():
    job = _ready_job()
    job["render_command_blueprint"] = {}
    job["render_command_blueprint_report"] = {}

    _blocked_with(job, "render_blueprint_missing")


def test_executor_blocks_when_blueprint_steps_missing():
    job = _ready_job()
    job["render_blueprint_steps"] = []
    job["render_command_blueprint"] = {}

    _blocked_with(job, "render_blueprint_steps_missing")


def test_executor_blocks_when_blueprint_not_non_executable():
    job = _ready_job()
    job["render_blueprint_non_executable"] = False

    _blocked_with(job, "render_blueprint_not_non_executable")


def test_executor_blocks_when_asset_manifest_missing():
    job = _ready_job()
    job["render_asset_manifest_report"] = {}

    _blocked_with(job, "render_asset_manifest_missing")


def test_executor_blocks_when_asset_manifest_failed():
    job = _ready_job()
    job["render_asset_manifest_status"] = "render_asset_manifest_failed"

    _blocked_with(job, "render_asset_manifest_not_ready")


def test_executor_blocks_on_dangerous_asset_manifest_flags():
    job = _ready_job()
    job["render_asset_can_write_files"] = True

    _blocked_with(job, "dangerous_asset_flag_enabled:render_asset_can_write_files")


def test_executor_creates_dry_run_steps_from_blueprint_steps():
    report = build_controlled_render_executor(_ready_job())

    assert report["status"] == "controlled_render_executor_dry_run_ready"
    assert report["total_steps"] == 2
    assert report["planned_step_count"] == 2
    assert report["executed_step_count"] == 0
    assert report["skipped_step_count"] == 2
    assert report["dry_run_only"] is True
    assert report["output_created"] is False
    assert report["output_path"] is None

    for step in report["execution_steps"]:
        assert step["would_execute"] is True
        assert step["executed"] is False
        assert step["skipped_reason"] == "dry_run_only_in_2b_50"
        assert step["safety_status"] == "dry_run_only"
        assert step["execution_mode"] == "dry_run"


def test_executor_blocks_real_render_requested_even_when_allowed_by_job_fields():
    job = _ready_job()
    job["render_execution_requested_mode"] = "real_render"
    job["render_execution_allow_real_render"] = True
    job["render_execution_allow_ffmpeg"] = True
    job["render_execution_allow_process_spawn"] = True
    job["render_execution_allow_media_write"] = True

    report = _blocked_with(
        job,
        "real_render_execution_not_implemented_in_2b_50",
    )

    assert report["real_render_requested"] is True
    assert report["real_render_allowed"] is False
    assert report["can_execute_real_render"] is False
    assert report["can_render"] is False
    assert report["can_run_ffmpeg"] is False
    assert report["can_spawn_process"] is False
    assert report["can_write_media"] is False
    assert report["output_created"] is False


def test_executor_uses_warning_status_when_approval_identity_missing():
    job = _ready_job()
    job["render_execution_approved_by"] = None

    report = build_controlled_render_executor(job)

    assert report["status"] == "controlled_render_executor_dry_run_with_warnings"
    assert "render_execution_approval_identity_missing" in report["warnings"]
    assert report["dry_run_only"] is True
    assert report["executed_step_count"] == 0
