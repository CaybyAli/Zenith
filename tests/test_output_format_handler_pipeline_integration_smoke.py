from __future__ import annotations

from models.job import Job


def test_output_format_handler_pipeline_runs_after_controlled_ffmpeg_execution():
    pipeline_text = open("core/gaming_pipeline.py", encoding="utf-8").read()

    assert "run_controlled_ff_exec_for_job" in pipeline_text
    assert "run_output_format_handler" in pipeline_text
    assert pipeline_text.index("run_controlled_ff_exec_for_job") < pipeline_text.index(
        "run_output_format_handler"
    )
    assert "OUTPUT_FORMAT_CONTRACT_STARTED" in pipeline_text
    assert "OUTPUT_FORMAT_CONTRACT_READY" in pipeline_text
    assert '"phase": "2B-55"' in pipeline_text
    assert '"output_format_contract_only": True' in pipeline_text
    assert '"render_preset_contract_only": True' in pipeline_text
    assert '"dry_run_only": True' in pipeline_text
    assert '"no_" "ff" "mpeg_execution_in_2b_55": True' in pipeline_text
    assert '"no_user_media_" "input_in_2b_55": True' in pipeline_text
    assert '"no_project_" "output_in_2b_55": True' in pipeline_text
    assert '"no_timeline_" "apply_in_2b_55": True' in pipeline_text


def test_job_from_dict_loads_output_format_fields_and_keeps_render_permissions_false():
    data = {
        "job_id": "job-output-format-from-dict",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "longform",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.5,
        "validator_status": "not_validated",
        "output_format_contract_report": {
            "status": "output_format_contract_ready_with_warnings"
        },
        "output_format_contract_status": "output_format_contract_ready_with_warnings",
        "output_format_selected_preset": "gaming_main_youtube_1080p60",
        "output_format_available_presets": [
            "gaming_main_youtube_1080p60",
            "fallback_youtube_1080p30",
        ],
        "output_format_selected_profile": "gaming_main",
        "output_format_selected_platform": "youtube",
        "output_format_selected_target_format": "longform",
        "output_video_spec": {"codec": "h264", "encoder_intent": "h264_nvenc"},
        "output_audio_spec": {"codec": "aac", "target_lufs": -14.0},
        "output_container_spec": {"container": "mp4", "extension": ".mp4"},
        "output_filename_hint": "safe.mp4",
        "output_safe_filename_hint": "safe.mp4",
        "output_path_hint": "safe.mp4",
        "output_can_prepare_output_format": True,
        "output_can_render": True,
        "output_can_write_project_output": True,
        "output_can_process_user_media": True,
        "output_can_execute_ffmpeg": True,
        "output_dry_run_only": True,
        "output_contract_only": True,
        "output_format_blocking_reasons": [],
        "output_format_warnings": ["nvenc_available_using_nvenc_intent"],
        "output_format_recommendation": "review_output_format_contract_warnings",
        "output_preset_requested": "gaming_main_youtube_1080p60",
        "output_platform_requested": "youtube",
        "output_resolution_requested": "1920x1080",
        "output_fps_requested": 60,
        "output_codec_preference": "h264",
        "output_audio_lufs_requested": -14.0,
        "output_container_requested": "mp4",
    }

    job = Job.from_dict(data)

    assert job.output_format_contract_report["status"] == (
        "output_format_contract_ready_with_warnings"
    )
    assert job.output_format_contract_status == "output_format_contract_ready_with_warnings"
    assert job.output_format_selected_preset == "gaming_main_youtube_1080p60"
    assert "fallback_youtube_1080p30" in job.output_format_available_presets
    assert job.output_format_selected_profile == "gaming_main"
    assert job.output_format_selected_platform == "youtube"
    assert job.output_format_selected_target_format == "longform"
    assert job.output_video_spec["encoder_intent"] == "h264_nvenc"
    assert job.output_audio_spec["target_lufs"] == -14.0
    assert job.output_container_spec["extension"] == ".mp4"
    assert job.output_safe_filename_hint == "safe.mp4"
    assert job.output_can_prepare_output_format is True

    assert job.output_can_render is False
    assert job.output_can_write_project_output is False
    assert job.output_can_process_user_media is False
    assert job.output_can_execute_ffmpeg is False

    assert job.output_dry_run_only is True
    assert job.output_contract_only is True
    assert job.output_format_warnings == ["nvenc_available_using_nvenc_intent"]
    assert job.output_preset_requested == "gaming_main_youtube_1080p60"
    assert job.output_platform_requested == "youtube"
    assert job.output_resolution_requested == "1920x1080"
    assert job.output_fps_requested == 60
    assert job.output_codec_preference == "h264"
    assert job.output_audio_lufs_requested == -14.0
    assert job.output_container_requested == "mp4"
