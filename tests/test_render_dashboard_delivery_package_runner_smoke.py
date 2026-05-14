from core.render_dashboard_delivery_package_runner import (
    run_render_dashboard_delivery_package,
)


def test_runner_writes_render_dashboard_delivery_fields_to_dict_job() -> None:
    job = {
        "job_id": "job_2b57_runner",
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

    report = run_render_dashboard_delivery_package(job)

    assert report["status"] == "render_dashboard_delivery_ready"
    assert job["render_dashboard_delivery_package_status"] == report["status"]
    assert len(job["render_dashboard_delivery_cards"]) == 11
    assert len(job["render_dashboard_delivery_panels"]) == 6
    assert len(job["render_dashboard_delivery_actions"]) == 10
    assert job["render_dashboard_delivery_dashboard_ready"] is True
    assert job["render_dashboard_delivery_dashboard_only"] is True
    assert job["render_dashboard_delivery_package_only"] is True

    assert job["render_dashboard_delivery_can_write_dashboard_file"] is False
    assert job["render_dashboard_delivery_can_move_video"] is False
    assert job["render_dashboard_delivery_can_copy_output"] is False
    assert job["render_dashboard_delivery_can_extract_thumbnail"] is False
    assert job["render_dashboard_delivery_can_render"] is False
    assert job["render_dashboard_delivery_can_run_ffmpeg"] is False
    assert job["render_dashboard_delivery_can_run_ffprobe"] is False
