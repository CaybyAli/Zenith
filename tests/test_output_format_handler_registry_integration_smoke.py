from __future__ import annotations

from core.output_format_handler import build_output_format_contract
from core.output_format_handler_signal_adapter import (
    build_output_format_contract_signals,
)


def _ready_job():
    return {
        "job_id": "registry-output-format",
        "profile": "gaming_main",
        "target_platforms": ["youtube"],
        "target_format": "longform",
        "ffmpeg_capability_resolver_report": {"status": "ffmpeg_capability_ready"},
        "ffmpeg_capability_status": "ffmpeg_capability_ready",
        "ffmpeg_has_h264": True,
        "ffmpeg_has_aac": True,
        "ffmpeg_has_nvenc": False,
        "ffmpeg_has_scale_filter": True,
        "ffmpeg_has_loudnorm_filter": False,
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
        "render_plan_output_targets": [{"platform": "youtube"}],
    }


def test_registry_file_collects_output_format_contract_signals():
    registry_text = open("core/unified_edit_signal_registry.py", encoding="utf-8").read()

    assert "build_output_format_contract_signals" in registry_text
    assert 'SOURCE_OUTPUT_FORMAT_CONTRACT = "output_format_contract"' in registry_text
    assert "output_format_contract_report = _job_attr(" in registry_text
    assert "source_counts[SOURCE_OUTPUT_FORMAT_CONTRACT]" in registry_text
    assert "_normalize_signal(" in registry_text
    assert "SOURCE_CONTROLLED_FF_EXECUTION" in registry_text
    assert registry_text.index("controlled_ff_exec_report = _job_attr(") < registry_text.index(
        "output_format_contract_report = _job_attr("
    )


def test_output_format_signal_adapter_emits_contract_and_preset_signals():
    job = _ready_job()
    report = build_output_format_contract(job).to_dict()
    job["output_format_contract_report"] = report

    signals = build_output_format_contract_signals(job)
    signal_types = {signal["signal_type"] for signal in signals}
    sources = {signal["source"] for signal in signals}

    assert sources == {"output_format_contract"}
    assert "output_format_contract_ready_with_warnings" in signal_types
    assert "output_format_preset_selected" in signal_types
    assert "output_format_video_spec_planned" in signal_types
    assert "output_format_audio_spec_planned" in signal_types
    assert "output_format_container_spec_planned" in signal_types
    assert "output_format_nvenc_fallback" in signal_types
    assert "output_format_loudnorm_missing" in signal_types
    assert "output_format_render_still_not_allowed" in signal_types

    for signal in signals:
        metadata = signal["metadata"]
        assert signal["action_hint"] == "review_output_format_contract"
        assert metadata["output_format_contract_only"] is True
        assert metadata["render_preset_contract_only"] is True
        assert metadata["dry_run_only"] is True
        assert metadata["no_full_render_in_2b_55"] is True
        assert metadata["no_ffmpeg_execution_in_2b_55"] is True
        assert metadata["no_user_media_input_in_2b_55"] is True
        assert metadata["no_project_output_in_2b_55"] is True
        assert metadata["no_timeline_apply_in_2b_55"] is True


def test_output_format_signal_adapter_blocks_permission_leak_in_report():
    job = _ready_job()
    report = build_output_format_contract(job).to_dict()
    report["can_render"] = True
    report["can_write_project_output"] = True
    report["can_process_user_media"] = True
    report["can_execute_ffmpeg"] = True
    job["output_format_contract_report"] = report

    signals = build_output_format_contract_signals(job)
    blocking_signals = [
        signal
        for signal in signals
        if signal["signal_type"] == "output_format_render_still_not_allowed"
        and signal["severity"] == "blocking"
    ]

    assert blocking_signals
