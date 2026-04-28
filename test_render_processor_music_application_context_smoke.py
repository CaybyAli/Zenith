from __future__ import annotations

import json
import os
import shutil
import subprocess

from moviepy import VideoFileClip

from core.render_processor import RenderProcessor
from models.edit_decision import EditDecision
from models.job import Job
from models.music_application_instruction import MusicApplicationInstruction
from models.music_application_plan import MusicApplicationPlan
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


def create_sample_video(output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x180:rate=10:duration=12",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1080:sample_rate=44100:duration=12",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def build_job(video_path: str) -> Job:
    return Job(
        job_id="job_render_processor_music_application_context_smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path=video_path,
    )


def main() -> None:
    test_dir = os.path.join("tmp", "render_processor_music_application_context_smoke")
    output_video = os.path.join("output", "job_render_processor_music_application_context_smoke_final.mp4")
    output_context = os.path.join("output", "job_render_processor_music_application_context_smoke_final_render_context.json")

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    if os.path.exists(output_video):
        os.remove(output_video)
    if os.path.exists(output_context):
        os.remove(output_context)

    video_path = os.path.join(test_dir, "sample_video.mp4")
    create_sample_video(video_path)

    job = build_job(video_path)

    edit_decision = EditDecision(
        job_id=job.job_id,
        selected_segments=["0.0s - end"],
        removed_segments=[],
        target_runtime=12.0,
        hook_candidate_range="0.0s - 3.0s",
        cut_style="basic_full_clip",
        cut_confidence=0.5,
    )

    final_edit_package = {
        "timeline_id": "timeline_001",
        "selected_segments": 2,
        "timeline_start_time": 3.0,
        "timeline_end_time": 8.0,
        "primary_focus_kind": "facecam",
        "render_strategy": "integrated_timeline_window",
        "reframe_instructions": 2,
        "reaction_moments": 3,
        "zoom_instructions": 3,
        "audio_cues": 2,
        "audio_mix_instructions": 2,
        "integration_score": 0.83,
    }

    music_application_plan = MusicApplicationPlan(
        plan_id="music_apply_001",
        job_id=job.job_id,
        channel_type="gaming_main",
        instructions=[
            MusicApplicationInstruction(
                instruction_id="apply_001",
                job_id=job.job_id,
                channel_type="gaming_main",
                asset_id="music_001",
                cue_kind="intro_bed",
                source_file_path="assets/audio/gaming_main/music/main_intro_bed.mp3",
                start_time=3.2,
                end_time=5.4,
                music_level=0.42,
                voice_priority=0.90,
                ducking_required=True,
                fade_in_seconds=0.35,
                fade_out_seconds=0.45,
                notes=[],
            ),
            MusicApplicationInstruction(
                instruction_id="apply_002",
                job_id=job.job_id,
                channel_type="gaming_main",
                asset_id="music_004",
                cue_kind="calm_bed",
                source_file_path="assets/audio/gaming_main/music/main_calm_bed.mp3",
                start_time=5.5,
                end_time=7.8,
                music_level=0.30,
                voice_priority=0.88,
                ducking_required=True,
                fade_in_seconds=0.50,
                fade_out_seconds=0.60,
                notes=[],
            ),
        ],
        application_score=0.86,
        notes=[],
    )

    rendered_path = RenderProcessor().render(
        job,
        edit_decision,
        final_edit_package=final_edit_package,
        music_application_plan=music_application_plan,
    )

    assert rendered_path == output_video
    assert os.path.exists(output_video)
    assert os.path.exists(output_context)

    with open(output_context, "r", encoding="utf-8") as f:
        context = json.load(f)

    assert context["used_final_edit_package"] is True
    assert context["music_application_plan_used"] is True
    assert context["music_application_instruction_count"] == 2
    assert context["applied_music_instruction_count"] == 2
    assert context["music_application_asset_ids"] == ["music_001", "music_004"]
    assert context["render_audio_strategy"] == "music_application_attached"

    with VideoFileClip(output_video) as clip:
        duration = float(clip.duration or 0.0)

    assert 4.5 <= duration <= 5.5

    print("RENDER PROCESSOR MUSIC APPLICATION CONTEXT SMOKE TEST PASSED")
    print(
        {
            "render_start_time": context["render_start_time"],
            "render_end_time": context["render_end_time"],
            "music_application_instruction_count": context["music_application_instruction_count"],
            "applied_music_instruction_count": context["applied_music_instruction_count"],
            "music_application_asset_ids": context["music_application_asset_ids"],
            "duration": round(duration, 3),
        }
    )


if __name__ == "__main__":
    main()