from __future__ import annotations

from copy import deepcopy

from core.controlled_render_executor import build_controlled_render_executor
from core.render_execution_permission_gate import build_render_execution_permission_gate


FALSE_EXECUTION_FLAGS = [
    "can_render",
    "can_run_ffmpeg",
    "can_spawn_process",
    "can_write_media",
    "can_apply_timeline",
    "can_execute_real_render",
    "real_render_allowed",
    "output_created",
]


def _blueprint_steps() -> list[dict]:
    return [
        {
            "step_id": "bp_step_1",
            "step_type": "trim",
            "order_index": 1,
            "source_segment_id": "seg_1",
            "description": "Dry-run trim planning only.",
            "can_execute_now": False,
            "requires_renderer_implementation": True,
        }
    ]


def _base_safe_job() -> dict:
    steps = _blueprint_steps()
    return {
        "job_id": "block8_pre_execution_audit_job",
        "render_readiness_status": "render_readiness_ready",
        "render_readiness_ready_for_next_render_stage": True,
        "render_readiness_can_render": False,
        "render_readiness_can_run_ffmpeg": False,
        "render_plan_status": "render_plan_ready",
        "render_plan_ready_for_renderer_contract": True,
        "render_plan_can_render": False,
        "render_plan_can_run_ffmpeg": False,
        "render_plan_can_write_media": False,
        "render_blueprint_status": "render_blueprint_ready",
        "render_blueprint_ready_for_renderer_implementation": True,
        "render_blueprint_non_executable": True,
        "render_blueprint_steps": steps,
        "render_command_blueprint": {"steps": steps},
        "render_command_blueprint_report": {
            "status": "render_blueprint_ready",
            "ready_for_renderer_implementation": True,
            "non_executable": True,
            "blueprint_steps": steps,
        },
        "render_blueprint_can_render": False,
        "render_blueprint_can_run_ffmpeg": False,
        "render_blueprint_can_spawn_process": False,
        "render_blueprint_can_write_media": False,
        "render_asset_manifest_status": "render_asset_manifest_ready",
        "render_asset_manifest_report": {
            "status": "render_asset_manifest_ready",
            "manifest_only": True,
            "paths_are_hints_only": True,
            "asset_references": [
                {
                    "asset_id": "source_video_hint",
                    "asset_type": "source_video",
                    "required": True,
                    "path_hint": "input_hint_only",
                    "safety_status": "safe_hint",
                    "blocking_reasons": [],
                }
            ],
            "output_path_plans": [
                {
                    "output_id": "dry_output_hint",
                    "output_type": "video",
                    "platform": "youtube",
                    "safe_filename": "planned_output_name_only",
                    "path_safety_status": "safe_hint",
                    "blocking_reasons": [],
                }
            ],
            "unsafe_path_count": 0,
            "missing_required_hint_count": 0,
            "can_render": False,
            "can_run_ffmpeg": False,
            "can_write_files": False,
        },
        "render_asset_unsafe_path_count": 0,
        "render_asset_missing_required_hint_count": 0,
        "render_asset_can_write_files": False,
        "render_asset_can_open_media": False,
        "render_asset_can_render": False,
        "render_asset_can_run_ffmpeg": False,
        "render_execution_human_approved": True,
        "render_execution_requested_status": "approved",
        "render_execution_approved_by": "Hajar",
        "render_execution_approved_at": "2026-05-14T00:00:00+00:00",
        "render_execution_approval_reason": "2B-51 safety audit fixture",
        "render_execution_requested_mode": "dry_run",
        "render_execution_allow_real_render": False,
        "render_execution_allow_ffmpeg": False,
        "render_execution_allow_process_spawn": False,
        "render_execution_allow_media_write": False,
    }


def _run_gate_and_executor(job: dict) -> tuple[dict, dict]:
    working = deepcopy(job)

    permission_report = build_render_execution_permission_gate(working)

    working["render_execution_permission_report"] = permission_report
    working["render_execution_permission_gate"] = permission_report
    working["render_execution_permission_status"] = permission_report["status"]
    working["render_execution_ready_for_real_render_stage"] = permission_report[
        "ready_for_real_render_stage"
    ]
    working["render_execution_can_prepare_real_render_execution"] = permission_report[
        "can_prepare_real_render_execution"
    ]
    working["render_execution_blocking_reasons"] = list(permission_report["blocking_reasons"])
    working["render_execution_human_approved"] = bool(permission_report["human_approved"])
    working["render_execution_approved_by"] = permission_report.get("approved_by")

    executor_report = build_controlled_render_executor(working)
    return permission_report, executor_report


def _assert_no_real_execution(report: dict) -> None:
    for key in FALSE_EXECUTION_FLAGS:
        if key in report:
            assert report[key] is False, f"{key} leaked as True"

    for step in report.get("execution_steps", []):
        assert step["execution_mode"] == "dry_run"
        assert step["executed"] is False
        assert step["safety_status"] == "dry_run_only"


def test_case_a_complete_safe_dry_run_allows_only_dry_run_data() -> None:
    permission, executor = _run_gate_and_executor(_base_safe_job())

    assert permission["status"] == "render_execution_permission_ready"
    assert permission["ready_for_real_render_stage"] is True
    assert permission["can_prepare_real_render_execution"] is True
    _assert_no_real_execution(permission)

    assert executor["status"] == "controlled_render_executor_dry_run_ready"
    assert executor["dry_run_only"] is True
    assert executor["executed_step_count"] == 0
    assert executor["planned_step_count"] == 1
    _assert_no_real_execution(executor)


def test_case_b_missing_human_approval_blocks_gate_and_executor() -> None:
    job = _base_safe_job()
    job["render_execution_human_approved"] = False
    job["render_execution_requested_status"] = None
    job["render_execution_approved_by"] = None
    job["render_execution_approved_at"] = None
    job["render_execution_approval_reason"] = None

    permission, executor = _run_gate_and_executor(job)

    assert permission["status"] == "render_execution_permission_blocked"
    assert "render_execution_human_approval_missing" in permission["blocking_reasons"]
    assert executor["status"] == "controlled_render_executor_blocked"
    _assert_no_real_execution(executor)


def test_case_c_render_plan_not_ready_blocks_later_execution() -> None:
    job = _base_safe_job()
    job["render_plan_status"] = "render_plan_blocked"
    job["render_plan_ready_for_renderer_contract"] = False

    permission, executor = _run_gate_and_executor(job)

    assert permission["status"] == "render_execution_permission_blocked"
    assert "render_plan_ready" in permission["blocking_reasons"]
    assert executor["status"] == "controlled_render_executor_blocked"
    _assert_no_real_execution(executor)


def test_case_d_executable_blueprint_risk_blocks_gate_and_executor() -> None:
    job = _base_safe_job()
    job["render_blueprint_non_executable"] = False
    job["render_command_blueprint_report"]["non_executable"] = False

    permission, executor = _run_gate_and_executor(job)

    assert permission["status"] == "render_execution_permission_blocked"
    assert "render_blueprint_non_executable" in permission["blocking_reasons"]
    assert executor["status"] == "controlled_render_executor_blocked"
    _assert_no_real_execution(executor)


def test_case_e_unsafe_asset_path_blocks_gate_and_executor() -> None:
    job = _base_safe_job()
    job["render_asset_unsafe_path_count"] = 1
    job["render_asset_blocking_reasons"] = ["unsafe_path_hint"]

    permission, executor = _run_gate_and_executor(job)

    assert permission["status"] == "render_execution_permission_blocked"
    assert "render_asset_manifest_safe" in permission["blocking_reasons"]
    assert executor["status"] == "controlled_render_executor_blocked"
    _assert_no_real_execution(executor)


def test_case_f_real_render_request_is_blocked_in_controlled_executor() -> None:
    job = _base_safe_job()
    job["render_execution_requested_mode"] = "real_render"
    job["render_execution_allow_real_render"] = True

    permission, executor = _run_gate_and_executor(job)

    assert permission["status"] == "render_execution_permission_ready"
    assert executor["status"] == "controlled_render_executor_blocked"
    assert executor["real_render_requested"] is True
    assert "real_render_execution_not_implemented_in_2b_50" in executor["blocking_reasons"]
    _assert_no_real_execution(executor)


def test_case_g_dangerous_permission_flag_leak_blocks_gate_and_executor() -> None:
    job = _base_safe_job()
    job["can_render"] = True
    job["render_plan_can_run_ffmpeg"] = True
    job["render_asset_can_write_files"] = True

    permission, executor = _run_gate_and_executor(job)

    assert permission["status"] == "render_execution_permission_blocked"
    assert "no_render_permission_leak" in permission["blocking_reasons"]
    assert "no_process_or_write_permission_leak" in permission["blocking_reasons"]
    assert executor["status"] == "controlled_render_executor_blocked"
    _assert_no_real_execution(executor)
