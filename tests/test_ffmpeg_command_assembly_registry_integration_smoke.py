from __future__ import annotations

from core.ffmpeg_command_assembly_runner import run_ffmpeg_command_assembly_for_job
from core.unified_edit_signal_registry import build_unified_edit_signal_result
from models.job import Job
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


def _ready_job() -> Job:
    return Job(
        job_id="ffmpeg-command-registry-smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        ffmpeg_capability_resolver_report={"status": "ffmpeg_capability_ready"},
        ffmpeg_capability_status="ffmpeg_capability_ready",
        ffmpeg_path_hint=r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
        ffmpeg_can_prepare_real_render_tools=True,
        ffmpeg_can_render=False,
        ffmpeg_can_process_media=False,
        ffmpeg_can_write_media=False,
        ffmpeg_can_probe_media_files=False,
        render_execution_permission_report={
            "status": "render_execution_permission_ready"
        },
        render_execution_permission_status="render_execution_permission_ready",
        render_execution_ready_for_real_render_stage=True,
        render_execution_can_prepare_real_render_execution=True,
        render_execution_human_approved=True,
        controlled_render_executor_report={
            "status": "controlled_render_executor_dry_run_ready"
        },
        controlled_render_executor_status="controlled_render_executor_dry_run_ready",
        controlled_render_dry_run_only=True,
        controlled_render_output_created=False,
        render_blueprint_non_executable=True,
        render_blueprint_steps=[
            {"step_id": "bp_trim_1", "step_type": "trim_concat"},
            {"step_id": "bp_encode_1", "step_type": "encode"},
        ],
        render_asset_paths_are_hints_only=True,
        render_asset_can_write_files=False,
        render_plan_segments=[{"segment_id": "seg_1"}],
        render_plan_output_targets=[{"target_id": "target_1"}],
        render_plan_operation_intents=[{"intent_type": "trim_concat"}],
    )


def test_registry_collects_ffmpeg_command_assembly_signals() -> None:
    job = _ready_job()
    run_ffmpeg_command_assembly_for_job(job)

    result = build_unified_edit_signal_result(job)
    data = result.to_dict() if hasattr(result, "to_dict") else result

    signals = data.get("signals", [])
    signal_types = {signal.get("signal_type") for signal in signals}
    sources = {signal.get("source") for signal in signals}

    assert "ffmpeg_command_assembly" in sources
    assert "ffmpeg_command_assembly_ready_with_warnings" in signal_types
    assert "ffmpeg_command_assembly_created" in signal_types
    assert "ffmpeg_command_argument_safe" in signal_types
    assert "ffmpeg_command_preview_only_confirmed" in signal_types
    assert "ffmpeg_command_real_execution_still_not_allowed" in signal_types
    assert "ffmpeg_command_ready_for_controlled_execution_stage" in signal_types

    assert data["source_counts"]["ffmpeg_command_assembly"] >= 1


def test_registry_collects_blocked_ffmpeg_command_assembly_signals() -> None:
    job = _ready_job()
    job.ffmpeg_capability_resolver_report = {}
    job.ffmpeg_capability_status = None

    run_ffmpeg_command_assembly_for_job(job)

    result = build_unified_edit_signal_result(job)
    data = result.to_dict() if hasattr(result, "to_dict") else result

    signals = data.get("signals", [])
    signal_types = {signal.get("signal_type") for signal in signals}

    assert "ffmpeg_command_assembly_blocked" in signal_types
    assert data["source_counts"]["ffmpeg_command_assembly"] >= 1
