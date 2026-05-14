from core.render_dashboard_delivery_package_builder import (
    build_render_dashboard_delivery_package,
)


def _base_job() -> dict:
    return {
        "job_id": "job_2b57_builder",
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
        "output_format_selected_preset": "youtube_1080p_h264_aac",
        "output_video_spec": {"width": 1920, "height": 1080, "fps": 60},
        "output_audio_spec": {"codec": "aac", "sample_rate": 48000},
        "output_container_spec": {"container": "mp4"},
        "output_safe_filename_hint": "safe_name.mp4",
        "render_verification_expected_spec": {"container": "mp4"},
        "render_verification_checks": [
            {"check_id": "container", "planned_only": True, "can_run_now": True},
            {"check_id": "video", "planned_only": True, "can_run_now": False},
        ],
        "render_verification_can_verify_smoke_output": True,
        "ffmpeg_has_nvenc": True,
        "ffmpeg_has_h264": True,
        "ffmpeg_has_aac": True,
        "ffmpeg_has_loudnorm_filter": True,
        "controlled_ffmpeg_output_created": True,
    }


def test_builder_creates_full_dashboard_delivery_package() -> None:
    package = build_render_dashboard_delivery_package(_base_job()).to_dict()

    assert package["status"] == "render_dashboard_delivery_ready"
    assert package["dashboard_ready"] is True
    assert package["dashboard_only"] is True
    assert package["package_only"] is True

    assert len(package["cards"]) == 11
    assert {card["card_id"] for card in package["cards"]} >= {
        "render_readiness",
        "render_plan",
        "render_blueprint",
        "asset_manifest",
        "human_approval_gate",
        "controlled_render_executor",
        "ffmpeg_capability",
        "ffmpeg_command_assembly",
        "controlled_ffmpeg_execution",
        "output_format_contract",
        "render_verification_contract",
    }

    assert {panel["panel_id"] for panel in package["panels"]} >= {
        "overview_panel",
        "safety_panel",
        "output_format_panel",
        "verification_panel",
        "ffmpeg_panel",
        "actions_panel",
    }

    assert package["output_summary"]["selected_preset"] == "youtube_1080p_h264_aac"
    assert package["verification_summary"]["total_checks"] == 2
    assert package["verification_summary"]["smoke_runnable_checks"] == 1
    assert package["ffmpeg_summary"]["nvenc_available"] is True


def test_builder_collects_warnings_and_blockers_for_status() -> None:
    warning_job = _base_job()
    warning_job["render_plan_warnings"] = ["plan warning"]
    warning_package = build_render_dashboard_delivery_package(warning_job).to_dict()

    assert warning_package["status"] == "render_dashboard_delivery_ready_with_warnings"
    assert warning_package["total_warnings"] == 1
    assert warning_package["dashboard_ready"] is True

    blocked_job = _base_job()
    blocked_job["render_verification_blocking_reasons"] = ["verification blocker"]
    blocked_package = build_render_dashboard_delivery_package(blocked_job).to_dict()

    assert blocked_package["status"] == "render_dashboard_delivery_blocked"
    assert blocked_package["total_blocking_reasons"] == 1
    assert blocked_package["dashboard_ready"] is False


def test_builder_blocks_real_actions_and_keeps_capabilities_false() -> None:
    package = build_render_dashboard_delivery_package(_base_job()).to_dict()

    blocked_action_ids = {
        "run_full_render",
        "move_output_to_dashboard",
        "extract_thumbnail",
        "probe_project_output",
        "publish_video",
    }
    blocked_actions = [
        action for action in package["actions"] if action["action_id"] in blocked_action_ids
    ]

    assert len(blocked_actions) == len(blocked_action_ids)
    assert all(action["enabled"] is False for action in blocked_actions)
    assert all(action["real_execution"] is True for action in blocked_actions)
    assert all(action["reason"] == "not_allowed_in_2b_57" for action in blocked_actions)

    assert package["can_write_dashboard_file"] is False
    assert package["can_move_video"] is False
    assert package["can_copy_output"] is False
    assert package["can_extract_thumbnail"] is False
    assert package["can_render"] is False
    assert package["can_run_ffmpeg"] is False
    assert package["can_run_ffprobe"] is False
