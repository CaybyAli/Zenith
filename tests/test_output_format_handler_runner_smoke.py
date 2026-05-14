from __future__ import annotations

from dataclasses import dataclass

from core.output_format_handler_runner import run_output_format_handler


def _ready_job():
    return {
        "job_id": "runner-job",
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
        "controlled_ffmpeg_execution_report": {"status": "controlled_ffmpeg_execution_ready"},
        "controlled_ffmpeg_execution_status": "controlled_ffmpeg_execution_ready",
        "controlled_ffmpeg_can_execute_full_render": False,
        "controlled_ffmpeg_can_render_timeline": False,
        "controlled_ffmpeg_can_process_user_media": False,
        "controlled_ffmpeg_can_write_project_output": False,
        "render_plan_output_targets": [{"platform": "youtube"}],
    }


@dataclass
class DummyJob:
    job_id: str = "dummy-job"
    profile: str = "gaming_main"
    target_platforms: list[str] = None
    target_format: str = "longform"
    ffmpeg_capability_resolver_report: dict = None
    ffmpeg_capability_status: str = "ffmpeg_capability_ready"
    ffmpeg_has_h264: bool = True
    ffmpeg_has_aac: bool = True
    ffmpeg_has_nvenc: bool = True
    ffmpeg_has_scale_filter: bool = True
    ffmpeg_has_loudnorm_filter: bool = True
    ffmpeg_can_prepare_real_render_tools: bool = True
    ffmpeg_blocking_reasons: list = None
    ffmpeg_command_assembly_report: dict = None
    ffmpeg_command_assembly_status: str = "ffmpeg_command_assembly_ready"
    ffmpeg_command_can_execute_commands: bool = False
    ffmpeg_command_can_render: bool = False
    ffmpeg_command_can_write_media: bool = False
    controlled_ffmpeg_execution_report: dict = None
    controlled_ffmpeg_execution_status: str = "controlled_ffmpeg_execution_ready"
    controlled_ffmpeg_can_execute_full_render: bool = False
    controlled_ffmpeg_can_render_timeline: bool = False
    controlled_ffmpeg_can_process_user_media: bool = False
    controlled_ffmpeg_can_write_project_output: bool = False
    render_plan_output_targets: list = None

    def __post_init__(self):
        self.target_platforms = ["youtube"]
        self.ffmpeg_capability_resolver_report = {"status": "ffmpeg_capability_ready"}
        self.ffmpeg_blocking_reasons = []
        self.ffmpeg_command_assembly_report = {"status": "ffmpeg_command_assembly_ready"}
        self.controlled_ffmpeg_execution_report = {"status": "controlled_ffmpeg_execution_ready"}
        self.render_plan_output_targets = [{"platform": "youtube"}]


def test_output_format_handler_runner_writes_dict_job_fields():
    job = _ready_job()

    report = run_output_format_handler(job)

    assert report["status"] == "output_format_contract_ready_with_warnings"
    assert job["output_format_contract_report"]["status"] == report["status"]
    assert job["output_format_selected_preset"] == "gaming_main_youtube_1080p60"
    assert "gaming_main_youtube_1080p60" in job["output_format_available_presets"]
    assert job["output_video_spec"]["encoder_intent"] == "libx264"
    assert job["output_audio_spec"]["codec"] == "aac"
    assert job["output_container_spec"]["container"] == "mp4"
    assert job["output_safe_filename_hint"].endswith(".mp4")
    assert job["output_can_prepare_output_format"] is True
    assert job["output_can_render"] is False
    assert job["output_can_write_project_output"] is False
    assert job["output_can_process_user_media"] is False
    assert job["output_can_execute_ffmpeg"] is False
    assert job["output_dry_run_only"] is True
    assert job["output_contract_only"] is True
    assert "nvenc_missing_falling_back_to_libx264" in job["output_format_warnings"]
    assert job["output_format_recommendation"] == "review_output_format_contract_warnings"


def test_output_format_handler_runner_writes_object_job_fields():
    job = DummyJob()

    report = run_output_format_handler(job)

    assert report["status"] == "output_format_contract_ready_with_warnings"
    assert job.output_format_contract_report["status"] == report["status"]
    assert job.output_format_selected_preset == "gaming_main_youtube_1080p60"
    assert job.output_video_spec["encoder_intent"] == "h264_nvenc"
    assert job.output_audio_spec["target_lufs"] == -14.0
    assert job.output_container_spec["extension"] == ".mp4"
    assert job.output_can_prepare_output_format is True
    assert job.output_can_render is False
    assert job.output_can_write_project_output is False
    assert job.output_can_process_user_media is False
    assert job.output_can_execute_ffmpeg is False
    assert job.output_dry_run_only is True
    assert job.output_contract_only is True
