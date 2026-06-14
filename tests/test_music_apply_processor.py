from __future__ import annotations

from core.music_apply_processor import MusicApplyProcessor
from models.music_apply_segment import MusicApplySegment
from models.music_apply_timeline import MusicApplyTimeline


def test_apply_passes_through_when_timeline_is_none(tmp_path):
    rendered_path = tmp_path / "rendered.mp4"

    result = MusicApplyProcessor().apply(
        rendered_video_path=rendered_path,
        music_application_plan=None,
        channel_type="gaming_main",
        music_apply_timeline=None,
    )

    assert result == {
        "music_applied": False,
        "output_video_path": str(rendered_path),
    }


def test_apply_passes_through_when_timeline_is_empty(tmp_path):
    rendered_path = tmp_path / "rendered.mp4"
    timeline = MusicApplyTimeline(
        timeline_id="timeline-empty",
        job_id="job-001",
        channel_type="gaming_main",
        segments=[],
    )

    result = MusicApplyProcessor().apply(
        rendered_video_path=rendered_path,
        music_application_plan=None,
        channel_type="gaming_main",
        music_apply_timeline=timeline,
    )

    assert result == {
        "music_applied": False,
        "output_video_path": str(rendered_path),
    }


def test_apply_non_empty_timeline_still_passes_through(tmp_path):
    rendered_path = tmp_path / "rendered.mp4"
    timeline = MusicApplyTimeline(
        timeline_id="timeline-001",
        job_id="job-001",
        channel_type="gaming_main",
        segments=[
            MusicApplySegment(
                segment_id="segment-001",
                job_id="job-001",
                asset_id="asset-001",
                cue_kind="intro_bed",
                source_file_path="local_assets/music/main_account/intro/test.mp3",
                video_start_time=1.0,
                video_end_time=5.0,
                music_offset_start=0.0,
                music_offset_end=4.0,
                music_level=0.35,
                voice_priority=0.9,
                ducking_required=True,
            )
        ],
    )

    result = MusicApplyProcessor().apply(
        rendered_video_path=rendered_path,
        music_application_plan=None,
        channel_type="gaming_main",
        music_apply_timeline=timeline,
    )

    assert result["music_applied"] is False
    assert result["output_video_path"] == str(rendered_path)
    assert result["music_apply_timeline_id"] == "timeline-001"
    assert result["music_apply_segment_count"] == 1
    assert result["music_apply_skeleton_pass_through"] is True
