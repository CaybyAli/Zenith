from __future__ import annotations

import re
from pathlib import Path

from core.unified_edit_signal_registry import build_unified_edit_signal_result


def _normalized_registry_text() -> str:
    text = Path("core/unified_edit_signal_registry.py").read_text(encoding="utf-8")
    return re.sub(r'["\']\s+["\']', "", text)


def _job_with_all_block8_reports() -> dict:
    return {
        "job_id": "job_2b58_registry",
        "render_readiness_guard_report": {
            "status": "render_readiness_ready",
            "checks": [],
        },
        "render_plan_report": {
            "status": "render_plan_ready",
            "steps": [],
        },
        "render_command_blueprint_report": {
            "status": "render_blueprint_ready",
            "non_executable": True,
            "commands": [],
        },
        "render_asset_manifest_report": {
            "status": "render_asset_manifest_ready",
            "assets": [],
        },
        "render_execution_permission_report": {
            "status": "render_execution_permission_ready",
            "human_approved": True,
            "checks": [],
        },
        "controlled_render_executor_report": {
            "status": "controlled_render_executor_dry_run_ready",
            "dry_run_only": True,
            "real_render_allowed": False,
            "execution_steps": [],
        },
        "ffmpeg_capability_resolver_report": {
            "status": "ffmpeg_capability_ready",
            "has_h264": True,
            "has_aac": True,
            "has_nvenc": True,
            "has_loudnorm_filter": True,
            "tool_probe_attempted": False,
            "tool_probe_succeeded": False,
        },
        "ffmpeg_command_assembly_report": {
            "status": "ffmpeg_command_assembly_ready",
            "dry_run_only": True,
            "can_execute_commands": False,
            "can_spawn_process": False,
            "can_render": False,
            "can_write_media": False,
            "assemblies": [],
        },
        "controlled_ffmpeg_execution_report": {
            "status": "controlled_ffmpeg_execution_dry_run_ready",
            "dry_run_only": True,
            "smoke_test_only": True,
            "output_created": False,
            "can_execute_full_render": False,
            "can_render_timeline": False,
            "can_process_user_media": False,
            "can_write_project_output": False,
        },
        "output_format_contract_report": {
            "status": "output_format_contract_ready",
            "can_prepare_output_format": True,
            "can_render": False,
            "can_execute_ffmpeg": False,
            "can_write_project_output": False,
            "can_process_user_media": False,
            "preset": {"preset_id": "gaming_main_youtube_1080p60"},
        },
        "render_verification_contract_report": {
            "status": "render_verification_contract_ready",
            "checks": [],
            "can_verify_project_output": False,
            "can_probe_media_files": False,
            "can_render": False,
            "can_write_media": False,
        },
        "render_dashboard_delivery_package_report": {
            "status": "render_dashboard_delivery_ready",
            "dashboard_ready": True,
            "cards": [],
            "panels": [],
            "actions": [],
            "can_write_dashboard_file": False,
            "can_move_video": False,
            "can_copy_output": False,
            "can_extract_thumbnail": False,
            "can_render": False,
        },
    }


def test_registry_declares_all_block8_signal_sources() -> None:
    text = _normalized_registry_text()

    required_sources = [
        "render_readiness_guard",
        "render_plan",
        "render_command_blueprint",
        "render_asset_manifest",
        "render_execution_permission_gate",
        "controlled_render_executor",
        "ffmpeg_capability_resolver",
        "ffmpeg_command_assembly",
        "controlled_ffmpeg_execution",
        "output_format_contract",
        "render_verification_contract",
        "render_dashboard_delivery_package",
    ]

    for source in required_sources:
        assert source in text, f"missing registry source: {source}"


def test_registry_collects_signals_from_all_block8_reports() -> None:
    result = build_unified_edit_signal_result(_job_with_all_block8_reports()).to_dict()

    expected_sources = {
        "render_readiness_guard",
        "render_plan",
        "render_command_blueprint",
        "render_asset_manifest",
        "render_execution_permission_gate",
        "controlled_render_executor",
        "ffmpeg_capability_resolver",
        "ffmpeg_command_assembly",
        "controlled_ffmpeg_execution",
        "output_format_contract",
        "render_verification_contract",
        "render_dashboard_delivery_package",
    }

    source_counts = result["source_counts"]

    for source in expected_sources:
        assert source_counts.get(source, 0) >= 1, f"no signals from {source}"


def test_registry_collects_required_ready_and_safety_signal_types() -> None:
    result = build_unified_edit_signal_result(_job_with_all_block8_reports()).to_dict()
    signal_types = {signal["signal_type"] for signal in result["signals"]}

    required_signal_types = {
        "render_readiness_ready",
        "render_plan_ready",
        "render_blueprint_ready",
        "render_asset_manifest_ready",
        "render_execution_permission_ready",
        "controlled_render_executor_dry_run_ready",
        "ffmpeg_capability_ready",
        "ffmpeg_command_assembly_ready",
        "controlled_ffmpeg_execution_dry_run_ready",
        "output_format_contract_ready",
        "render_verification_contract_ready",
        "render_dashboard_delivery_ready",
        "controlled_ffmpeg_full_render_still_not_allowed",
        "output_format_render_still_not_allowed",
        "render_verification_project_output_still_not_allowed",
        "render_dashboard_no_file_write_confirmed",
        "render_dashboard_no_video_move_confirmed",
        "render_dashboard_no_thumbnail_extract_confirmed",
    }

    missing = sorted(required_signal_types - signal_types)
    assert missing == []
