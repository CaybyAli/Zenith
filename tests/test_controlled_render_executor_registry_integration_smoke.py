from __future__ import annotations

from core.controlled_render_executor_runner import run_controlled_render_executor_for_job
from core.controlled_render_executor_signal_adapter import (
    build_controlled_render_executor_signals,
)
from core.unified_edit_signal_registry import (
    SOURCE_CONTROLLED_RENDER_EXECUTOR,
    build_unified_edit_signal_result,
)


def _ready_job() -> dict:
    return {
        "job_id": "job_2b50_registry",
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


def _signal_types(signals: list[dict]) -> set[str]:
    return {str(signal.get("signal_type")) for signal in signals}


def test_signal_adapter_reports_dry_run_ready_and_step_planned():
    job = _ready_job()
    run_controlled_render_executor_for_job(job)

    signals = build_controlled_render_executor_signals(job)
    types = _signal_types(signals)

    assert "controlled_render_executor_dry_run_ready" in types
    assert "controlled_render_execution_step_planned" in types
    assert "controlled_render_dry_run_only_confirmed" in types
    assert "controlled_render_real_render_not_allowed_here" in types

    for signal in signals:
        assert signal["source"] == "controlled_render_executor"
        assert signal["action_hint"] == "review_controlled_render_executor"
        assert signal["metadata"]["controlled_render_executor_foundation"] is True
        assert signal["metadata"]["dry_run_only"] is True
        assert signal["metadata"]["media_unchanged"] is True
        assert signal["metadata"]["no_real_render_in_2b_50"] is True


def test_signal_adapter_reports_blocked_real_render_request():
    job = _ready_job()
    job["render_execution_requested_mode"] = "real_render"
    job["render_execution_allow_real_render"] = True
    run_controlled_render_executor_for_job(job)

    signals = build_controlled_render_executor_signals(job)
    types = _signal_types(signals)

    assert "controlled_render_executor_blocked" in types
    assert "controlled_render_real_render_requested_blocked" in types
    assert "controlled_render_real_render_not_allowed_here" in types


def test_signal_adapter_reports_permission_gate_not_ready():
    job = _ready_job()
    job["render_execution_permission_status"] = "render_execution_permission_blocked"
    run_controlled_render_executor_for_job(job)

    signals = build_controlled_render_executor_signals(job)
    types = _signal_types(signals)

    assert "controlled_render_executor_blocked" in types
    assert "controlled_render_permission_gate_not_ready" in types


def test_signal_adapter_reports_blueprint_missing():
    job = _ready_job()
    job["render_command_blueprint"] = {}
    job["render_command_blueprint_report"] = {}
    run_controlled_render_executor_for_job(job)

    signals = build_controlled_render_executor_signals(job)
    types = _signal_types(signals)

    assert "controlled_render_executor_blocked" in types
    assert "controlled_render_blueprint_missing" in types


def test_signal_adapter_reports_asset_manifest_not_ready():
    job = _ready_job()
    job["render_asset_manifest_status"] = "render_asset_manifest_failed"
    run_controlled_render_executor_for_job(job)

    signals = build_controlled_render_executor_signals(job)
    types = _signal_types(signals)

    assert "controlled_render_executor_blocked" in types
    assert "controlled_render_asset_manifest_not_ready" in types


def test_registry_collects_controlled_render_executor_signals():
    job = _ready_job()
    run_controlled_render_executor_for_job(job)

    result = build_unified_edit_signal_result(job)

    assert SOURCE_CONTROLLED_RENDER_EXECUTOR in result.source_counts
    assert result.source_counts[SOURCE_CONTROLLED_RENDER_EXECUTOR] >= 4

    types = _signal_types(result.signals)
    assert "controlled_render_executor_dry_run_ready" in types
    assert "controlled_render_execution_step_planned" in types
    assert "controlled_render_dry_run_only_confirmed" in types
    assert "controlled_render_real_render_not_allowed_here" in types


def test_registry_warns_when_controlled_render_report_missing():
    result = build_unified_edit_signal_result({"job_id": "missing_2b50_report"})

    assert f"no_signals_from_{SOURCE_CONTROLLED_RENDER_EXECUTOR}" in result.warnings
