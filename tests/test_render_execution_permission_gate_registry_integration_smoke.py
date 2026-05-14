from __future__ import annotations

from core.render_execution_permission_gate_runner import (
    run_render_execution_permission_gate_for_job,
)
from core.render_execution_permission_gate_signal_adapter import (
    build_render_execution_permission_gate_signals,
)
from core.unified_edit_signal_registry import (
    SOURCE_RENDER_EXECUTION_PERMISSION_GATE,
    build_unified_edit_signal_result,
)


def _ready_job() -> dict:
    return {
        "job_id": "job_2b49_registry",
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


def _signal_types(signals: list[dict]) -> set[str]:
    return {str(signal.get("signal_type")) for signal in signals}


def test_signal_adapter_reports_ready_and_real_render_still_not_allowed_here():
    job = _ready_job()
    run_render_execution_permission_gate_for_job(job)

    signals = build_render_execution_permission_gate_signals(job)
    types = _signal_types(signals)

    assert "render_execution_permission_ready" in types
    assert "render_execution_human_approval_present" in types
    assert "render_execution_ready_for_real_render_stage" in types
    assert "render_execution_real_render_still_not_allowed_here" in types

    for signal in signals:
        assert signal["source"] == "render_execution_permission_gate"
        assert signal["action_hint"] == "review_render_execution_permission"
        assert signal["metadata"]["render_execution_permission_gate_only"] is True
        assert signal["metadata"]["final_human_approval_gate"] is True
        assert signal["metadata"]["media_unchanged"] is True
        assert signal["metadata"]["no_execution_in_2b_49"] is True
        assert signal["metadata"]["no_render_in_2b_49"] is True


def test_signal_adapter_reports_human_approval_missing():
    job = _ready_job()
    job["render_execution_human_approved"] = False
    job["render_execution_requested_status"] = None
    run_render_execution_permission_gate_for_job(job)

    signals = build_render_execution_permission_gate_signals(job)
    types = _signal_types(signals)

    assert "render_execution_permission_blocked" in types
    assert "render_execution_human_approval_missing" in types


def test_signal_adapter_reports_rejected_approval():
    job = _ready_job()
    job["render_execution_requested_status"] = "rejected"
    job["render_execution_rejected_by"] = "Hajar"
    run_render_execution_permission_gate_for_job(job)

    signals = build_render_execution_permission_gate_signals(job)
    types = _signal_types(signals)

    assert "render_execution_permission_blocked" in types
    assert "render_execution_approval_rejected" in types


def test_signal_adapter_reports_previous_gate_failures():
    job = _ready_job()
    job["render_plan_status"] = "render_plan_blocked"
    run_render_execution_permission_gate_for_job(job)

    signals = build_render_execution_permission_gate_signals(job)
    types = _signal_types(signals)

    assert "render_execution_permission_blocked" in types
    assert "render_execution_plan_not_ready" in types


def test_signal_adapter_reports_permission_leak_blocked():
    job = _ready_job()
    job["render_blueprint_can_spawn_process"] = True
    run_render_execution_permission_gate_for_job(job)

    signals = build_render_execution_permission_gate_signals(job)
    types = _signal_types(signals)

    assert "render_execution_permission_blocked" in types
    assert "render_execution_permission_leak_blocked" in types


def test_registry_collects_render_execution_permission_signals():
    job = _ready_job()
    run_render_execution_permission_gate_for_job(job)

    result = build_unified_edit_signal_result(job)

    assert SOURCE_RENDER_EXECUTION_PERMISSION_GATE in result.source_counts
    assert result.source_counts[SOURCE_RENDER_EXECUTION_PERMISSION_GATE] >= 4

    types = _signal_types(result.signals)
    assert "render_execution_permission_ready" in types
    assert "render_execution_human_approval_present" in types
    assert "render_execution_ready_for_real_render_stage" in types
    assert "render_execution_real_render_still_not_allowed_here" in types


def test_registry_warns_when_permission_report_missing():
    result = build_unified_edit_signal_result({"job_id": "missing_2b49_report"})

    assert (
        f"no_signals_from_{SOURCE_RENDER_EXECUTION_PERMISSION_GATE}"
        in result.warnings
    )
