from __future__ import annotations

from core.render_verification_contract_runner import run_render_verification_contract
from core.render_verification_contract_signal_adapter import (
    build_render_verification_contract_signals,
)
from core.unified_edit_signal_registry import build_unified_edit_signal_result


def _ready_job(**overrides):
    job = {
        "job_id": "job_registry_verify",
        "output_format_contract_report": {"status": "output_format_contract_ready"},
        "output_format_contract_status": "output_format_contract_ready",
        "output_can_prepare_output_format": True,
        "output_can_render": False,
        "output_can_write_project_output": False,
        "output_can_process_user_media": False,
        "output_can_execute_ffmpeg": False,
        "output_video_spec": {
            "codec": "h264",
            "resolution_width": 1920,
            "resolution_height": 1080,
            "fps": 60,
        },
        "output_audio_spec": {"codec": "aac"},
        "output_container_spec": {"container": "mp4", "faststart": True},
        "render_plan_estimated_output_duration_seconds": 12.0,
        "render_verification_duration_tolerance_seconds": 1.0,
        "ffprobe_path_hint": "ffprobe",
    }
    job.update(overrides)
    return job


def test_signal_adapter_builds_render_verification_signals():
    job = _ready_job()
    run_render_verification_contract(job)

    signals = build_render_verification_contract_signals(job)
    signal_types = {signal["signal_type"] for signal in signals}

    assert "render_verification_contract_ready" in signal_types
    assert "render_verification_expected_spec_planned" in signal_types
    assert "render_verification_check_planned" in signal_types
    assert "render_verification_probe_plan_created" in signal_types
    assert "render_verification_project_output_still_not_allowed" in signal_types
    assert "render_verification_media_probe_still_not_allowed" in signal_types
    assert all(signal["source"] == "render_verification_contract" for signal in signals)
    assert all(signal["action_hint"] == "review_render_verification_contract" for signal in signals)


def test_registry_collects_render_verification_contract_signals():
    job = _ready_job()
    run_render_verification_contract(job)

    result = build_unified_edit_signal_result(job)
    result_dict = result.to_dict()
    signals = result_dict["signals"]
    signal_types = {signal["signal_type"] for signal in signals}

    assert result_dict["source_counts"]["render_verification_contract"] >= 1
    assert "render_verification_contract_ready" in signal_types
    assert "render_verification_probe_plan_created" in signal_types
    assert "render_verification_project_output_still_not_allowed" in signal_types
    assert "render_verification_media_probe_still_not_allowed" in signal_types


def test_registry_collects_smoke_probe_available_signal_when_allowed():
    job = _ready_job(
        controlled_ffmpeg_output_created=True,
        controlled_ffmpeg_output_path="smoke.mp4",
        controlled_ffmpeg_smoke_test_only=True,
        render_verification_allow_smoke_probe=True,
    )
    run_render_verification_contract(job)

    result = build_unified_edit_signal_result(job)
    signal_types = {signal["signal_type"] for signal in result.to_dict()["signals"]}

    assert "render_verification_contract_smoke_probe_ready" in signal_types
    assert "render_verification_smoke_probe_available" in signal_types
