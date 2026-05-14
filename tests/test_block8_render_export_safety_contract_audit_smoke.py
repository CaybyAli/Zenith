from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.controlled_ffmpeg_execution import (
    _build_internal_smoke_command,
    build_controlled_ffmpeg_execution_report,
)
from core.output_format_handler import build_output_format_contract
from core.render_dashboard_delivery_package_builder import (
    build_render_dashboard_delivery_package,
)
from core.render_execution_permission_gate import build_render_execution_permission_gate
from core.render_verification_contract import build_render_verification_contract


def _permission_job(**overrides) -> dict:
    job = {
        "job_id": "job_2b58_permission",
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
        "render_execution_approval_reason": "2B-58 audit approval",
    }
    job.update(overrides)
    return job


def _controlled_job(**overrides) -> SimpleNamespace:
    data = {
        "job_id": "job_2b58_controlled",
        "render_execution_permission_status": "render_execution_permission_ready",
        "render_execution_human_approved": True,
        "render_execution_ready_for_real_render_stage": True,
        "render_execution_can_prepare_real_render_execution": True,
        "render_execution_blocking_reasons": [],
        "ffmpeg_capability_status": "ffmpeg_capability_ready",
        "ffmpeg_path_hint": "C:/Tools/ffmpeg/bin/ffmpeg.exe",
        "ffmpeg_can_prepare_real_render_tools": True,
        "ffmpeg_can_render": False,
        "ffmpeg_can_process_media": False,
        "ffmpeg_can_write_media": False,
        "ffmpeg_blocking_reasons": [],
        "ffmpeg_command_assembly_status": "ffmpeg_command_assembly_ready",
        "ffmpeg_command_ready_for_controlled_execution_stage": True,
        "ffmpeg_command_can_execute_commands": False,
        "ffmpeg_command_can_spawn_process": False,
        "ffmpeg_command_can_render": False,
        "ffmpeg_command_can_write_media": False,
        "ffmpeg_command_blocking_reasons": [],
        "ffmpeg_execution_requested_mode": "dry_run",
        "ffmpeg_execution_allow_real_render": False,
        "ffmpeg_execution_allow_ffmpeg_execution": False,
        "ffmpeg_execution_allow_process_spawn": False,
        "ffmpeg_execution_allow_media_write": False,
        "ffmpeg_execution_smoke_duration_seconds": 1.0,
        "ffmpeg_execution_smoke_output_dir_hint": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _output_job(**overrides) -> dict:
    job = {
        "job_id": "job_2b58_output",
        "profile": "gaming_main",
        "target_platforms": ["youtube"],
        "target_format": "longform",
        "ffmpeg_capability_resolver_report": {"status": "ffmpeg_capability_ready"},
        "ffmpeg_capability_status": "ffmpeg_capability_ready",
        "ffmpeg_has_h264": True,
        "ffmpeg_has_aac": True,
        "ffmpeg_has_nvenc": True,
        "ffmpeg_has_scale_filter": True,
        "ffmpeg_has_loudnorm_filter": True,
        "ffmpeg_can_prepare_real_render_tools": True,
        "ffmpeg_blocking_reasons": [],
        "ffmpeg_command_assembly_report": {"status": "ffmpeg_command_assembly_ready"},
        "ffmpeg_command_assembly_status": "ffmpeg_command_assembly_ready",
        "ffmpeg_command_can_execute_commands": False,
        "ffmpeg_command_can_render": False,
        "ffmpeg_command_can_write_media": False,
        "controlled_ffmpeg_execution_report": {
            "status": "controlled_ffmpeg_execution_ready"
        },
        "controlled_ffmpeg_execution_status": "controlled_ffmpeg_execution_ready",
        "controlled_ffmpeg_can_execute_full_render": False,
        "controlled_ffmpeg_can_render_timeline": False,
        "controlled_ffmpeg_can_process_user_media": False,
        "controlled_ffmpeg_can_write_project_output": False,
        "render_plan_output_targets": [
            {"platform": "youtube", "target_format": "longform"}
        ],
    }
    job.update(overrides)
    return job


def _verification_job(**overrides) -> dict:
    job = {
        "job_id": "job_2b58_verify",
        "output_format_contract_report": {"status": "output_format_contract_ready"},
        "output_format_contract_status": "output_format_contract_ready",
        "output_can_prepare_output_format": True,
        "output_can_render": False,
        "output_can_write_project_output": False,
        "output_can_process_user_media": False,
        "output_can_execute_ffmpeg": False,
        "output_video_spec": {
            "codec": "h264",
            "encoder_intent": "h264_nvenc",
            "resolution_width": 1920,
            "resolution_height": 1080,
            "fps": 60,
        },
        "output_audio_spec": {
            "codec": "aac",
            "target_lufs": -14.0,
            "true_peak_db": -1.0,
        },
        "output_container_spec": {
            "container": "mp4",
            "extension": ".mp4",
            "faststart": True,
        },
        "render_plan_estimated_output_duration_seconds": 12.0,
        "render_verification_duration_tolerance_seconds": 1.0,
        "ffprobe_path_hint": "ffprobe",
        "controlled_ffmpeg_output_created": False,
        "controlled_ffmpeg_output_path": None,
        "controlled_ffmpeg_smoke_test_only": True,
        "render_verification_allow_smoke_probe": False,
    }
    job.update(overrides)
    return job


def _dashboard_job(**overrides) -> dict:
    job = {
        "job_id": "job_2b58_dashboard",
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
        ],
        "render_verification_can_verify_smoke_output": True,
        "ffmpeg_has_nvenc": True,
        "ffmpeg_has_h264": True,
        "ffmpeg_has_aac": True,
        "ffmpeg_has_loudnorm_filter": True,
        "controlled_ffmpeg_output_created": True,
    }
    job.update(overrides)
    return job


def test_case_a_complete_safe_block8_path_never_grants_real_render_permissions() -> None:
    permission = build_render_execution_permission_gate(_permission_job())
    assert permission["status"] == "render_execution_permission_ready"
    assert permission["can_render"] is False
    assert permission["can_run_ffmpeg"] is False
    assert permission["can_spawn_process"] is False
    assert permission["can_write_media"] is False
    assert permission["can_apply_timeline"] is False

    controlled = build_controlled_ffmpeg_execution_report(_controlled_job())
    assert controlled.status == "controlled_ffmpeg_execution_dry_run_ready"
    assert controlled.can_execute_full_render is False
    assert controlled.can_render_timeline is False
    assert controlled.can_process_user_media is False
    assert controlled.can_write_project_output is False

    output = build_output_format_contract(_output_job()).to_dict()
    assert output["status"] in {
        "output_format_contract_ready",
        "output_format_contract_ready_with_warnings",
    }
    assert output["can_prepare_output_format"] is True
    assert output["can_render"] is False
    assert output["can_execute_ffmpeg"] is False

    verification = build_render_verification_contract(_verification_job()).to_dict()
    assert verification["status"] == "render_verification_contract_ready"
    assert verification["can_verify_project_output"] is False
    assert verification["can_probe_media_files"] is False
    assert verification["can_render"] is False

    dashboard = build_render_dashboard_delivery_package(_dashboard_job()).to_dict()
    assert dashboard["dashboard_ready"] is True
    assert dashboard["can_write_dashboard_file"] is False
    assert dashboard["can_move_video"] is False
    assert dashboard["can_copy_output"] is False
    assert dashboard["can_extract_thumbnail"] is False
    assert dashboard["can_render"] is False


def test_case_b_missing_human_approval_blocks_and_later_stages_do_not_gain_render_rights() -> None:
    permission = build_render_execution_permission_gate(
        _permission_job(
            render_execution_human_approved=False,
            render_execution_requested_status=None,
        )
    )

    assert permission["status"] == "render_execution_permission_blocked"
    assert "render_execution_human_approval_missing" in permission["blocking_reasons"]
    assert permission["can_render"] is False

    controlled = build_controlled_ffmpeg_execution_report(
        _controlled_job(render_execution_human_approved=False)
    )
    assert controlled.status == "controlled_ffmpeg_execution_blocked"
    assert controlled.can_execute_full_render is False
    assert controlled.can_render_timeline is False


def test_case_c_missing_ffmpeg_capability_blocks_without_render_rights() -> None:
    output = build_output_format_contract(
        _output_job(
            ffmpeg_capability_resolver_report={},
            ffmpeg_capability_status=None,
            ffmpeg_has_h264=False,
            ffmpeg_has_aac=False,
        )
    ).to_dict()

    assert output["status"] == "output_format_contract_blocked"
    assert output["can_render"] is False
    assert output["can_execute_ffmpeg"] is False
    assert output["can_write_project_output"] is False


def test_case_d_command_assembly_execution_leak_creates_blocker() -> None:
    output = build_output_format_contract(
        _output_job(
            ffmpeg_command_can_execute_commands=True,
            ffmpeg_command_can_render=True,
            ffmpeg_command_can_write_media=True,
        )
    ).to_dict()

    assert output["status"] == "output_format_contract_blocked"
    assert "ffmpeg_command_execution_permission_leak" in output["blocking_reasons"]
    assert output["can_render"] is False
    assert output["can_execute_ffmpeg"] is False


def test_case_e_controlled_ffmpeg_smoke_is_lavfi_only_and_not_full_render(tmp_path) -> None:
    command = _build_internal_smoke_command(
        ffmpeg_path="C:/Tools/ffmpeg/bin/ffmpeg.exe",
        output_path=tmp_path / "smoke.mp4",
        duration_seconds=1.0,
    )
    joined = " ".join(command)

    assert "lavfi" in command
    assert any("testsrc" in item for item in command)
    assert any("sine=frequency=1000" in item for item in command)
    assert "raw_video_path" not in joined
    assert "user_media" not in joined

    report = build_controlled_ffmpeg_execution_report(
        _controlled_job(
            ffmpeg_execution_requested_mode="smoke_test",
            ffmpeg_execution_allow_real_render=True,
            ffmpeg_execution_allow_ffmpeg_execution=True,
            ffmpeg_execution_allow_process_spawn=True,
            ffmpeg_execution_allow_media_write=True,
        )
    )

    assert report.status == "controlled_ffmpeg_execution_smoke_ready"
    assert report.smoke_test_only is True
    assert report.can_execute_full_render is False
    assert report.can_render_timeline is False
    assert report.can_process_user_media is False
    assert report.can_write_project_output is False


def test_case_f_output_format_contract_ready_but_no_execution_permissions() -> None:
    report = build_output_format_contract(_output_job()).to_dict()

    assert report["can_prepare_output_format"] is True
    assert report["can_render"] is False
    assert report["can_execute_ffmpeg"] is False
    assert report["can_write_project_output"] is False
    assert report["can_process_user_media"] is False


def test_case_g_verification_contract_ready_but_no_project_probe_or_render() -> None:
    report = build_render_verification_contract(_verification_job()).to_dict()

    assert report["can_verify_project_output"] is False
    assert report["can_probe_media_files"] is False
    assert report["can_render"] is False
    assert report["can_write_media"] is False


def test_case_h_dashboard_delivery_ready_but_only_data_package() -> None:
    report = build_render_dashboard_delivery_package(_dashboard_job()).to_dict()

    assert report["dashboard_ready"] is True
    assert report["can_write_dashboard_file"] is False
    assert report["can_move_video"] is False
    assert report["can_copy_output"] is False
    assert report["can_extract_thumbnail"] is False
    assert report["can_render"] is False
