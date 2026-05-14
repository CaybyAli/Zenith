from core.render_dashboard_delivery_package_runner import (
    run_render_dashboard_delivery_package,
)
from core.unified_edit_signal_registry import build_unified_edit_signal_result


def test_registry_collects_render_dashboard_delivery_signals() -> None:
    job = {
        "job_id": "job_2b57_registry",
        "render_readiness_status": "render_readiness_ready",
        "render_plan_status": "render_plan_ready",
        "render_blueprint_status": "render_blueprint_ready",
        "render_asset_manifest_status": "render_asset_manifest_ready",
        "render_execution_permission_status": "render_execution_permission_ready",
        "controlled_render_executor_status": "controlled_render_executor_ready",
        "ffmpeg_capability_status": "ffmpeg_capability_ready",
        "ffmpeg_command_assembly_status": "ffmpeg_command_assembly_ready",
        "controlled_ffmpeg_execution_status": "controlled_ffmpeg_execution_smoke_ready",
        "output_format_contract_status": "output_format_contract_ready",
        "render_verification_contract_status": "render_verification_contract_ready",
    }
    run_render_dashboard_delivery_package(job)

    result = build_unified_edit_signal_result(job)
    data = result.to_dict()

    assert data["source_counts"]["render_dashboard_delivery_package"] >= 1

    signal_types = {signal["signal_type"] for signal in data["signals"]}
    assert "render_dashboard_delivery_ready" in signal_types
    assert "render_dashboard_card_created" in signal_types
    assert "render_dashboard_panel_created" in signal_types
    assert "render_dashboard_action_enabled" in signal_types
    assert "render_dashboard_action_disabled" in signal_types
    assert "render_dashboard_safety_summary_ready" in signal_types
    assert "render_dashboard_output_summary_ready" in signal_types
    assert "render_dashboard_verification_summary_ready" in signal_types
    assert "render_dashboard_no_file_write_confirmed" in signal_types
    assert "render_dashboard_no_video_move_confirmed" in signal_types
    assert "render_dashboard_no_thumbnail_extract_confirmed" in signal_types
