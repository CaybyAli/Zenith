from __future__ import annotations

from core.render_execution_permission_gate import build_render_execution_permission_gate


def _ready_job() -> dict:
    return {
        "job_id": "job_2b49_smoke",
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


def _check_ids(report: dict) -> set[str]:
    return {str(check["check_id"]) for check in report["checks"]}


def _blocked_with(job: dict, expected_reason: str) -> None:
    report = build_render_execution_permission_gate(job)

    assert report["status"] == "render_execution_permission_blocked"
    assert report["ready_for_real_render_stage"] is False
    assert report["can_prepare_real_render_execution"] is False
    assert expected_reason in report["blocking_reasons"] or expected_reason in _check_ids(report)
    assert report["can_render"] is False
    assert report["can_run_ffmpeg"] is False
    assert report["can_spawn_process"] is False
    assert report["can_write_media"] is False
    assert report["can_apply_timeline"] is False


def test_gate_blocks_when_render_readiness_missing():
    job = _ready_job()
    job["render_readiness_status"] = None
    job["render_readiness_ready_for_next_render_stage"] = False

    _blocked_with(job, "render_readiness_ready")


def test_gate_blocks_when_render_readiness_not_ready():
    job = _ready_job()
    job["render_readiness_status"] = "render_readiness_blocked"

    _blocked_with(job, "render_readiness_ready")


def test_gate_blocks_when_render_plan_missing():
    job = _ready_job()
    job["render_plan_status"] = None
    job["render_plan_ready_for_renderer_contract"] = False

    _blocked_with(job, "render_plan_ready")


def test_gate_blocks_when_render_plan_not_ready():
    job = _ready_job()
    job["render_plan_status"] = "render_plan_blocked"

    _blocked_with(job, "render_plan_ready")


def test_gate_blocks_when_render_blueprint_missing():
    job = _ready_job()
    job["render_blueprint_status"] = None
    job["render_blueprint_ready_for_renderer_implementation"] = False

    _blocked_with(job, "render_blueprint_ready")


def test_gate_blocks_when_blueprint_not_ready():
    job = _ready_job()
    job["render_blueprint_status"] = "render_blueprint_blocked"

    _blocked_with(job, "render_blueprint_ready")


def test_gate_blocks_when_blueprint_not_non_executable():
    job = _ready_job()
    job["render_blueprint_non_executable"] = False

    _blocked_with(job, "render_blueprint_non_executable")


def test_gate_blocks_when_asset_manifest_missing():
    job = _ready_job()
    job["render_asset_manifest_status"] = None

    _blocked_with(job, "render_asset_manifest_ready")


def test_gate_blocks_when_asset_manifest_failed():
    job = _ready_job()
    job["render_asset_manifest_status"] = "render_asset_manifest_failed"

    _blocked_with(job, "render_asset_manifest_ready")


def test_gate_blocks_when_asset_manifest_has_unsafe_paths():
    job = _ready_job()
    job["render_asset_unsafe_path_count"] = 1

    _blocked_with(job, "render_asset_manifest_safe")


def test_gate_blocks_when_asset_manifest_has_missing_required_hints():
    job = _ready_job()
    job["render_asset_missing_required_hint_count"] = 1

    _blocked_with(job, "render_asset_manifest_safe")


def test_gate_blocks_on_previous_blocking_reasons():
    job = _ready_job()
    job["render_plan_blocking_reasons"] = ["render_plan_has_problem"]

    _blocked_with(job, "no_blocking_reasons")


def test_gate_blocks_on_render_permission_leak():
    job = _ready_job()
    job["render_blueprint_can_render"] = True

    _blocked_with(job, "no_render_permission_leak")


def test_gate_blocks_on_tool_or_write_permission_leak():
    job = _ready_job()
    job["render_blueprint_can_run_ffmpeg"] = True

    _blocked_with(job, "no_process_or_write_permission_leak")


def test_gate_blocks_on_file_write_permission_leak():
    job = _ready_job()
    job["render_plan_can_write_media"] = True

    _blocked_with(job, "no_process_or_write_permission_leak")


def test_gate_blocks_on_timeline_permission_leak():
    job = _ready_job()
    job["render_plan_can_apply_timeline"] = True

    _blocked_with(job, "no_timeline_apply_permission_leak")


def test_gate_blocks_when_human_approval_missing():
    job = _ready_job()
    job["render_execution_human_approved"] = False
    job["render_execution_requested_status"] = None

    _blocked_with(job, "render_execution_human_approval_missing")


def test_gate_blocks_when_approval_rejected():
    job = _ready_job()
    job["render_execution_requested_status"] = "rejected"
    job["render_execution_rejected_by"] = "Hajar"

    _blocked_with(job, "render_execution_approval_rejected")


def test_gate_blocks_when_approval_identity_missing():
    job = _ready_job()
    job["render_execution_approved_by"] = None

    _blocked_with(job, "render_execution_approval_identity_missing")


def test_gate_ready_when_everything_is_safe_and_human_approved():
    report = build_render_execution_permission_gate(_ready_job())

    assert report["status"] == "render_execution_permission_ready"
    assert report["ready_for_real_render_stage"] is True
    assert report["can_prepare_real_render_execution"] is True
    assert report["human_approved"] is True
    assert report["approved_by"] == "Hajar"
    assert report["blocking_count"] == 0
    assert report["warning_count"] == 0
    assert report["can_render"] is False
    assert report["can_run_ffmpeg"] is False
    assert report["can_spawn_process"] is False
    assert report["can_write_media"] is False
    assert report["can_apply_timeline"] is False


def test_gate_ready_with_warning_when_timestamp_missing():
    job = _ready_job()
    job["render_execution_approved_at"] = None

    report = build_render_execution_permission_gate(job)

    assert report["status"] == "render_execution_permission_ready_with_warnings"
    assert report["ready_for_real_render_stage"] is True
    assert report["can_prepare_real_render_execution"] is True
    assert "human_approval_timestamp_present" in _check_ids(report)
    assert "render_execution_approval_timestamp_missing" in report["warnings"]


def test_gate_accepts_requested_status_approved_variant():
    job = _ready_job()
    job["render_execution_human_approved"] = False
    job["render_execution_requested_status"] = "approved"

    report = build_render_execution_permission_gate(job)

    assert report["status"] == "render_execution_permission_ready"
    assert report["human_approved"] is True
    assert report["ready_for_real_render_stage"] is True


def test_gate_blocks_when_render_already_started_hint_exists():
    job = _ready_job()
    job["render_execution_started"] = True

    _blocked_with(job, "render_not_started")
