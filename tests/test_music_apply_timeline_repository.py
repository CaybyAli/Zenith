from __future__ import annotations

import json

from core.music_apply_timeline_repository import MusicApplyTimelineRepository


def test_load_timeline_returns_none_when_file_missing(tmp_path):
    assert MusicApplyTimelineRepository().load_timeline(tmp_path) is None


def test_load_timeline_reads_json_mini_fixture(tmp_path):
    payload = {
        "timeline_id": "timeline-001",
        "job_id": "job-001",
        "channel_type": "gaming_main",
        "segments": [
            {
                "segment_id": "segment-001",
                "job_id": "job-001",
                "asset_id": "asset-001",
                "cue_kind": "intro_bed",
                "source_file_path": "local_assets/music/main_account/intro/test.mp3",
                "video_start_time": 1.0,
                "video_end_time": 5.0,
                "music_offset_start": 0.25,
                "music_offset_end": 4.25,
                "music_level": 0.35,
                "voice_priority": 0.9,
                "ducking_required": True,
                "fade_in_seconds": 0.2,
                "fade_out_seconds": 0.3,
                "notes": ["mini fixture"],
            }
        ],
        "timeline_score": 0.82,
        "notes": ["repository test"],
    }
    (tmp_path / "music_apply_timeline.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    loaded = MusicApplyTimelineRepository().load_timeline(tmp_path)

    assert loaded is not None
    assert loaded.timeline_id == "timeline-001"
    assert loaded.job_id == "job-001"
    assert loaded.channel_type == "gaming_main"
    assert loaded.timeline_score == 0.82
    assert loaded.notes == ["repository test"]
    assert len(loaded.segments) == 1
    assert loaded.segments[0].segment_id == "segment-001"
    assert loaded.segments[0].asset_id == "asset-001"
    assert loaded.segments[0].ducking_required is True
