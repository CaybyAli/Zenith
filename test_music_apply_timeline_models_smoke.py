from __future__ import annotations

from models.music_apply_segment import MusicApplySegment
from models.music_apply_timeline import MusicApplyTimeline


def main() -> None:
    segment = MusicApplySegment(
        segment_id="music_apply_seg_001",
        job_id="job_music_apply_timeline_models_smoke",
        asset_id="music_001",
        cue_kind="intro_bed",
        source_file_path="assets/audio/gaming_main/music/main_intro_bed.mp3",
        video_start_time=10.0,
        video_end_time=24.0,
        music_offset_start=0.0,
        music_offset_end=14.0,
        music_level=0.42,
        voice_priority=0.90,
        ducking_required=True,
        fade_in_seconds=0.35,
        fade_out_seconds=0.45,
        notes=["timeline smoke"],
    )

    timeline = MusicApplyTimeline(
        timeline_id="music_apply_timeline_001",
        job_id="job_music_apply_timeline_models_smoke",
        channel_type="gaming_main",
        segments=[segment],
        timeline_score=0.84,
        notes=["music apply timeline smoke"],
    )

    assert len(timeline.segments) == 1
    assert timeline.segments[0].asset_id == "music_001"
    assert timeline.segments[0].music_offset_end == 14.0
    assert timeline.timeline_score == 0.84

    print("MUSIC APPLY TIMELINE MODELS SMOKE TEST PASSED")
    print(
        {
            "segments": len(timeline.segments),
            "asset_id": timeline.segments[0].asset_id,
            "timeline_score": timeline.timeline_score,
        }
    )


if __name__ == "__main__":
    main()