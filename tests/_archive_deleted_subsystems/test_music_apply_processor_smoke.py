from __future__ import annotations

import json
import os
import shutil
import subprocess

from moviepy import VideoFileClip

from core.music_apply_processor import MusicApplyProcessor
from models.music_apply_segment import MusicApplySegment
from models.music_apply_timeline import MusicApplyTimeline


def create_sample_video(output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cmd = [
        r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x180:rate=10:duration=8",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1110:sample_rate=44100:duration=8",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def create_sample_music(output_path: str, frequency: int) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cmd = [
        r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency={frequency}:sample_rate=44100:duration=5",
        "-c:a",
        "libmp3lame",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def main() -> None:
    test_dir = os.path.join("tmp", "music_apply_processor_smoke")

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    video_path = os.path.join(test_dir, "rendered_video.mp4")
    music_path_1 = os.path.join(test_dir, "music_track_1.mp3")
    music_path_2 = os.path.join(test_dir, "music_track_2.mp3")

    create_sample_video(video_path)
    create_sample_music(music_path_1, 620)
    create_sample_music(music_path_2, 520)

    timeline = MusicApplyTimeline(
        timeline_id="music_apply_timeline_smoke_001",
        job_id="job_music_apply_processor_smoke",
        channel_type="gaming_main",
        segments=[
            MusicApplySegment(
                segment_id="music_apply_seg_001",
                job_id="job_music_apply_processor_smoke",
                asset_id="music_001",
                cue_kind="intro_bed",
                source_file_path=music_path_1,
                video_start_time=1.0,
                video_end_time=3.5,
                music_offset_start=0.0,
                music_offset_end=2.5,
                music_level=0.35,
                voice_priority=0.90,
                ducking_required=True,
                fade_in_seconds=0.25,
                fade_out_seconds=0.40,
                notes=[],
            ),
            MusicApplySegment(
                segment_id="music_apply_seg_002",
                job_id="job_music_apply_processor_smoke",
                asset_id="music_002",
                cue_kind="calm_bed",
                source_file_path=music_path_2,
                video_start_time=4.0,
                video_end_time=7.0,
                music_offset_start=0.0,
                music_offset_end=3.0,
                music_level=0.28,
                voice_priority=0.88,
                ducking_required=True,
                fade_in_seconds=0.35,
                fade_out_seconds=0.45,
                notes=[],
            ),
        ],
        timeline_score=0.84,
        notes=[],
    )

    result = MusicApplyProcessor().apply(
        rendered_video_path=video_path,
        music_application_plan=None,
        channel_type="gaming_main",
        music_apply_timeline=timeline,
    )

    assert result["music_applied"] is True
    assert result["music_apply_timeline_source"] == "pipeline"
    assert result["music_apply_timeline_id"] == timeline.timeline_id
    assert result["music_apply_segment_count"] == 2
    assert result["applied_music_segment_count"] == 2
    assert result["music_application_asset_ids"] == ["music_001", "music_002"]
    assert os.path.exists(result["output_video_path"])

    context_path = os.path.join(test_dir, "rendered_video_music_apply_context.json")
    assert os.path.exists(context_path)

    with open(context_path, "r", encoding="utf-8") as f:
        context = json.load(f)

    assert context["music_applied"] is True
    assert context["music_apply_timeline_source"] == "pipeline"
    assert context["music_apply_timeline_id"] == timeline.timeline_id

    with VideoFileClip(result["output_video_path"]) as clip:
        duration = float(clip.duration or 0.0)

    assert 7.5 <= duration <= 8.5

    print("MUSIC APPLY PROCESSOR SMOKE TEST PASSED")
    print(
        {
            "music_applied": result["music_applied"],
            "music_apply_timeline_source": result["music_apply_timeline_source"],
            "music_apply_timeline_id": result["music_apply_timeline_id"],
            "music_application_asset_ids": result["music_application_asset_ids"],
            "duration": round(duration, 3),
        }
    )


if __name__ == "__main__":
    main()