from __future__ import annotations

import os
import shutil
import subprocess
from types import SimpleNamespace

from core.shorts_generator import ShortsGenerator
from models.publish_package import PublishPackage
from shared.enums import ChannelType, PlatformType, TargetFormat


def create_sample_video(output_path: str, duration: int, frequency: int) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cmd = [
        r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=size=320x180:rate=10:duration={duration}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency={frequency}:sample_rate=44100:duration={duration}",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def main() -> None:
    test_dir = os.path.join("tmp", "shorts_generator_uses_raw_source_smoke")
    export_root = os.path.join("exports", "gaming_main", "job_shorts_raw_source_smoke")

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    if os.path.exists(export_root):
        shutil.rmtree(export_root)

    os.makedirs(test_dir, exist_ok=True)

    final_video_path = os.path.join(test_dir, "final_60s.mp4")
    raw_video_path = os.path.join(test_dir, "raw_220s.mp4")

    create_sample_video(final_video_path, duration=60, frequency=1180)
    create_sample_video(raw_video_path, duration=220, frequency=680)

    package = PublishPackage(
        job_id="job_shorts_raw_source_smoke",
        video_path=final_video_path,
        source_video_path=raw_video_path,
        title="Shorts Raw Source Smoke",
        description="Smoke",
        hashtags=["#zenith"],
        thumbnail_path=None,
        platform=PlatformType.YOUTUBE,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        requires_manual_approval=True,
        title_mode="youtube_title",
        description_mode="youtube_description",
        hashtags_mode="youtube_optional",
        subtitle_style="youtube_standard",
        packaging_profile="youtube",
        length_profile="longform_or_shortform",
        preferred_aspect_ratio="16:9_or_9:16",
        thumbnail_required=False,
        uploader_backend="youtube",
        variant_id="variant_shorts_raw_source_smoke",
    )

    shorts_decision = SimpleNamespace(
        shorts_count=2,
        selected_segments=[
            {
                "label": "70.0s - 115.0s",
                "start_seconds": 70.0,
                "end_seconds": 115.0,
                "duration_seconds": 45.0,
                "score": 0.9,
                "selection_reason": "raw_source_test",
            },
            {
                "label": "150.0s - 195.0s",
                "start_seconds": 150.0,
                "end_seconds": 195.0,
                "duration_seconds": 45.0,
                "score": 0.9,
                "selection_reason": "raw_source_test",
            },
        ],
    )

    shorts = ShortsGenerator().generate(
        package,
        shorts_decision,
        platform_targets=["youtube", "tiktok"],
    )

    assert len(shorts) == 2

    for short in shorts:
        assert os.path.exists(short["path"])
        assert os.path.getsize(short["path"]) > 0

    print("SHORTS GENERATOR USES RAW SOURCE SMOKE TEST PASSED")
    print(
        {
            "shorts_count": len(shorts),
            "paths": [short["path"] for short in shorts],
        }
    )


if __name__ == "__main__":
    main()