from __future__ import annotations

import os
import shutil

from core.music_apply_timeline_repository import MusicApplyTimelineRepository
from models.music_apply_segment import MusicApplySegment
from models.music_apply_timeline import MusicApplyTimeline


def main() -> None:
    test_dir = os.path.join("tmp", "music_apply_timeline_repository_smoke")
    export_path = os.path.join(test_dir, "export")

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    timeline = MusicApplyTimeline(
        timeline_id="music_apply_timeline_repo_001",
        job_id="job_music_apply_timeline_repository_smoke",
        channel_type="gaming_main",
        segments=[
            MusicApplySegment(
                segment_id="music_apply_seg_001",
                job_id="job_music_apply_timeline_repository_smoke",
                asset_id="music_001",
                cue_kind="intro_bed",
                source_file_path="assets/audio/gaming_main/music/main_intro_bed.mp3",
                video_start_time=10.0,
                video_end_time=20.0,
                music_offset_start=0.0,
                music_offset_end=10.0,
                music_level=0.42,
                voice_priority=0.90,
                ducking_required=True,
                fade_in_seconds=0.35,
                fade_out_seconds=0.45,
                notes=["repo smoke"],
            ),
            MusicApplySegment(
                segment_id="music_apply_seg_002",
                job_id="job_music_apply_timeline_repository_smoke",
                asset_id="music_004",
                cue_kind="calm_bed",
                source_file_path="assets/audio/gaming_main/music/main_calm_bed.mp3",
                video_start_time=20.0,
                video_end_time=28.0,
                music_offset_start=0.0,
                music_offset_end=8.0,
                music_level=0.30,
                voice_priority=0.88,
                ducking_required=True,
                fade_in_seconds=0.50,
                fade_out_seconds=0.60,
                notes=["repo smoke"],
            ),
        ],
        timeline_score=0.82,
        notes=["timeline repository smoke"],
    )

    repo = MusicApplyTimelineRepository()
    saved_path = repo.save_timeline(export_path, timeline)
    loaded = repo.load_timeline(export_path)

    assert os.path.exists(saved_path)
    assert loaded is not None
    assert loaded.timeline_id == timeline.timeline_id
    assert len(loaded.segments) == 2
    assert loaded.segments[0].asset_id == "music_001"
    assert loaded.segments[1].video_start_time == 20.0

    print("MUSIC APPLY TIMELINE REPOSITORY SMOKE TEST PASSED")
    print(
        {
            "saved_path": saved_path,
            "segments": len(loaded.segments),
            "timeline_score": loaded.timeline_score,
        }
    )


if __name__ == "__main__":
    main()