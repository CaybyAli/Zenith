from __future__ import annotations

from core.ffmpeg_command_assembly_runner import run_ffmpeg_command_assembly_for_job
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
        job_id="ffmpeg-command-runner-smoke",
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


def test_runner_writes_ffmpeg_command_job_fields() -> None:
    job = _ready_job()

    report = run_ffmpeg_command_assembly_for_job(job)

    assert report.status == "ffmpeg_command_assembly_ready_with_warnings"
    assert job.ffmpeg_command_assembly_status == report.status
    assert job.ffmpeg_command_assembly_report["status"] == report.status
    assert job.ffmpeg_command_total_assemblies == report.total_assemblies
    assert job.ffmpeg_command_safe_assembly_count == report.safe_assembly_count
    assert job.ffmpeg_command_blocked_assembly_count == 0
    assert job.ffmpeg_command_assemblies
    assert isinstance(job.ffmpeg_command_assemblies[0]["argv_preview"], list)
    assert isinstance(job.ffmpeg_command_assemblies[0]["argument_tokens"], list)

    assert job.ffmpeg_command_dry_run_only is True
    assert job.ffmpeg_command_assembly_only is True
    assert job.ffmpeg_command_preview_only is True
    assert job.ffmpeg_command_ready_for_controlled_execution_stage is True

    assert job.ffmpeg_command_can_execute_commands is False
    assert job.ffmpeg_command_can_spawn_process is False
    assert job.ffmpeg_command_can_render is False
    assert job.ffmpeg_command_can_write_media is False
    assert job.ffmpeg_command_can_probe_media_files is False


def test_runner_blocks_missing_requirements_and_writes_reasons() -> None:
    job = _ready_job()
    job.ffmpeg_capability_resolver_report = {}
    job.ffmpeg_capability_status = None

    report = run_ffmpeg_command_assembly_for_job(job)

    assert report.status == "ffmpeg_command_assembly_blocked"
    assert job.ffmpeg_command_assembly_status == "ffmpeg_command_assembly_blocked"
    assert "ffmpeg_capability_resolver_report_missing" in job.ffmpeg_command_blocking_reasons
    assert job.ffmpeg_command_ready_for_controlled_execution_stage is False
    assert job.ffmpeg_command_can_render is False
    assert job.ffmpeg_command_can_spawn_process is False


def test_job_from_dict_loads_ffmpeg_command_fields_and_keeps_permissions_false() -> None:
    data = _ready_job().to_dict()
    data.update(
        {
            "ffmpeg_command_assembly_report": {
                "status": "ffmpeg_command_assembly_ready"
            },
            "ffmpeg_command_assembly_status": "ffmpeg_command_assembly_ready",
            "ffmpeg_command_assemblies": [
                {
                    "assembly_id": "a1",
                    "argv_preview": [r"D:\Tools\ffmpeg\bin\ffmpeg.exe"],
                    "argument_tokens": [],
                }
            ],
            "ffmpeg_command_total_assemblies": 1,
            "ffmpeg_command_safe_assembly_count": 1,
            "ffmpeg_command_blocked_assembly_count": 0,
            "ffmpeg_command_dry_run_only": True,
            "ffmpeg_command_assembly_only": True,
            "ffmpeg_command_preview_only": True,
            "ffmpeg_command_ready_for_controlled_execution_stage": True,
            "ffmpeg_command_can_execute_commands": True,
            "ffmpeg_command_can_spawn_process": True,
            "ffmpeg_command_can_render": True,
            "ffmpeg_command_can_write_media": True,
            "ffmpeg_command_can_probe_media_files": True,
            "ffmpeg_command_blocking_reasons": [],
            "ffmpeg_command_warnings": ["argument_placeholder_preview_only"],
            "ffmpeg_command_recommendation": "review_ffmpeg_command_assembly",
        }
    )

    loaded = Job.from_dict(data)

    assert loaded.ffmpeg_command_assembly_status == "ffmpeg_command_assembly_ready"
    assert loaded.ffmpeg_command_total_assemblies == 1
    assert loaded.ffmpeg_command_safe_assembly_count == 1
    assert loaded.ffmpeg_command_ready_for_controlled_execution_stage is True
    assert loaded.ffmpeg_command_warnings == ["argument_placeholder_preview_only"]

    assert loaded.ffmpeg_command_can_execute_commands is False
    assert loaded.ffmpeg_command_can_spawn_process is False
    assert loaded.ffmpeg_command_can_render is False
    assert loaded.ffmpeg_command_can_write_media is False
    assert loaded.ffmpeg_command_can_probe_media_files is False
