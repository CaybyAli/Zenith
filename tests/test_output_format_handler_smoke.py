from __future__ import annotations

import re

from core.output_format_handler import build_output_format_contract


def _ready_job(**overrides):
    job = {
        "job_id": "job:test/unsafe name",
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
        "controlled_ffmpeg_execution_report": {"status": "controlled_ffmpeg_execution_ready"},
        "controlled_ffmpeg_execution_status": "controlled_ffmpeg_execution_ready",
        "controlled_ffmpeg_can_execute_full_render": False,
        "controlled_ffmpeg_can_render_timeline": False,
        "controlled_ffmpeg_can_process_user_media": False,
        "controlled_ffmpeg_can_write_project_output": False,
        "render_plan_output_targets": [{"platform": "youtube", "target_format": "longform"}],
    }
    job.update(overrides)
    return job


def test_output_format_handler_blocks_when_ffmpeg_capability_report_missing():
    report = build_output_format_contract(
        {
            "job_id": "missing-capability",
            "controlled_ffmpeg_execution_report": {"status": "controlled_ffmpeg_execution_ready"},
            "controlled_ffmpeg_execution_status": "controlled_ffmpeg_execution_ready",
        }
    ).to_dict()

    assert report["status"] == "output_format_contract_blocked"
    assert "ffmpeg_capability_report_missing" in report["blocking_reasons"]
    assert report["can_prepare_output_format"] is False


def test_output_format_handler_blocks_when_ffmpeg_capability_blocked():
    report = build_output_format_contract(
        _ready_job(
            ffmpeg_capability_status="ffmpeg_capability_blocked",
            ffmpeg_capability_resolver_report={"status": "ffmpeg_capability_blocked"},
        )
    ).to_dict()

    assert report["status"] == "output_format_contract_blocked"
    assert "ffmpeg_capability_status_not_ready" in report["blocking_reasons"]


def test_output_format_handler_blocks_when_h264_missing():
    report = build_output_format_contract(_ready_job(ffmpeg_has_h264=False)).to_dict()

    assert report["status"] == "output_format_contract_blocked"
    assert "ffmpeg_h264_missing" in report["blocking_reasons"]


def test_output_format_handler_blocks_when_aac_missing():
    report = build_output_format_contract(_ready_job(ffmpeg_has_aac=False)).to_dict()

    assert report["status"] == "output_format_contract_blocked"
    assert "ffmpeg_aac_missing" in report["blocking_reasons"]


def test_output_format_handler_warns_when_nvenc_missing_and_uses_libx264():
    report = build_output_format_contract(_ready_job(ffmpeg_has_nvenc=False)).to_dict()

    assert report["status"] == "output_format_contract_ready_with_warnings"
    assert "nvenc_missing_falling_back_to_libx264" in report["warnings"]
    assert report["preset"]["video"]["encoder_intent"] == "libx264"


def test_output_format_handler_uses_h264_nvenc_when_available():
    report = build_output_format_contract(_ready_job(ffmpeg_has_nvenc=True)).to_dict()

    assert report["preset"]["video"]["codec"] == "h264"
    assert report["preset"]["video"]["encoder_intent"] == "h264_nvenc"
    assert "nvenc_available_using_nvenc_intent" in report["warnings"]


def test_output_format_handler_warns_when_loudnorm_missing():
    report = build_output_format_contract(_ready_job(ffmpeg_has_loudnorm_filter=False)).to_dict()

    assert "loudnorm_filter_missing_audio_normalization_may_be_limited" in report["warnings"]
    assert report["preset"]["audio"]["loudnorm_required"] is True


def test_output_format_handler_exposes_required_presets():
    report = build_output_format_contract(_ready_job()).to_dict()

    assert "gaming_main_youtube_1080p60" in report["available_presets"]
    assert "gaming_uncut_youtube_1080p60" in report["available_presets"]
    assert "shorts_vertical_1080x1920_60" in report["available_presets"]
    assert "fallback_youtube_1080p30" in report["available_presets"]


def test_output_format_handler_selects_requested_preset_when_available():
    report = build_output_format_contract(
        _ready_job(output_preset_requested="gaming_uncut_youtube_1080p60")
    ).to_dict()

    assert report["preset"]["preset_id"] == "gaming_uncut_youtube_1080p60"
    assert report["preset"]["video"]["crf"] == 20


def test_output_format_handler_falls_back_cleanly():
    report = build_output_format_contract(
        _ready_job(
            profile="unknown_profile",
            target_platforms=["unknown_platform"],
            output_preset_requested="does_not_exist",
        )
    ).to_dict()

    assert report["preset"]["preset_id"] == "fallback_youtube_1080p30"
    assert "requested_output_preset_unknown_using_fallback" in report["warnings"]


def test_output_format_handler_video_audio_container_specs_are_complete():
    report = build_output_format_contract(_ready_job()).to_dict()
    video = report["preset"]["video"]
    audio = report["preset"]["audio"]
    container = report["preset"]["container"]

    assert video["codec"] == "h264"
    assert video["encoder_intent"] == "h264_nvenc"
    assert video["resolution_width"] == 1920
    assert video["resolution_height"] == 1080
    assert video["fps"] == 60
    assert video["crf"] == 18
    assert video["preset"] == "fast"
    assert video["pix_fmt"] == "yuv420p"

    assert audio["codec"] == "aac"
    assert audio["bitrate_kbps"] == 320
    assert audio["target_lufs"] == -14.0
    assert audio["true_peak_db"] == -1.0

    assert container["container"] == "mp4"
    assert container["extension"] == ".mp4"
    assert container["faststart"] is True
    assert container["movflags"] == "+faststart"


def test_output_format_handler_safe_filename_hint_is_safe():
    report = build_output_format_contract(_ready_job()).to_dict()
    safe_name = report["preset"]["safe_filename_hint"]

    assert safe_name.endswith(".mp4")
    assert re.fullmatch(r"[A-Za-z0-9._-]+", safe_name)


def test_output_format_handler_can_prepare_but_never_unblocks_render_permissions():
    report = build_output_format_contract(_ready_job()).to_dict()

    assert report["can_prepare_output_format"] is True
    assert report["can_render"] is False
    assert report["can_write_project_output"] is False
    assert report["can_process_user_media"] is False
    assert report["can_execute_ffmpeg"] is False
    assert report["dry_run_only"] is True
    assert report["contract_only"] is True


def test_output_format_handler_blocks_permission_leaks_from_previous_ffmpeg_stages():
    report = build_output_format_contract(
        _ready_job(
            ffmpeg_command_can_execute_commands=True,
            ffmpeg_command_can_render=True,
            ffmpeg_command_can_write_media=True,
            controlled_ffmpeg_can_execute_full_render=True,
            controlled_ffmpeg_can_render_timeline=True,
            controlled_ffmpeg_can_process_user_media=True,
            controlled_ffmpeg_can_write_project_output=True,
        )
    ).to_dict()

    assert report["status"] == "output_format_contract_blocked"
    assert "ffmpeg_command_execution_permission_leak" in report["blocking_reasons"]
    assert "controlled_ffmpeg_output_permission_leak" in report["blocking_reasons"]
    assert report["can_render"] is False
    assert report["can_write_project_output"] is False
    assert report["can_process_user_media"] is False
    assert report["can_execute_ffmpeg"] is False
