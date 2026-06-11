from pathlib import Path

import pytest

from core.music_timeline_planner import (
    MUSIC_CATEGORY_FAIL,
    MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND,
    MUSIC_CATEGORY_HYPE,
    MUSIC_CATEGORY_SAD,
    MUSIC_CATEGORY_VLOG_BACKGROUND,
    MOOD_FAIL,
    MOOD_FUNNY,
    MOOD_HYPE,
    MOOD_NEUTRAL_BACKGROUND,
    MOOD_SAD,
    build_fallback_video_mood_timeline,
    classify_music_track_category,
    compute_adaptive_track_gain,
    mood_to_music_category,
    plan_music_timeline,
)


def _tracks(category: str = MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND, count: int = 4, duration: float = 150.0):
    means = [-18.0, -20.0, -23.0, -28.0, -25.0, -21.0, -19.0, -24.0]
    return [
        {
            "path": f"local_assets/music/main_account/{category}/track_{index}.mp3",
            "category": category,
            "duration_sec": duration,
            "mean_volume_db": means[index % len(means)],
        }
        for index in range(count)
    ]


def _assert_covers_video(plan: dict, duration: float) -> None:
    assert plan["music_timeline"]
    assert plan["music_timeline"][0]["start_sec"] == 0.0
    assert plan["music_timeline"][-1]["end_sec"] == pytest.approx(duration, abs=0.01)
    for segment in plan["music_timeline"]:
        assert 0.0 <= segment["start_sec"] < segment["end_sec"] <= duration
        assert segment["track_used_duration_sec"] <= segment["track_duration_sec"]


def test_8_8_minute_video_uses_multiple_duration_based_songs():
    mood = build_fallback_video_mood_timeline(528.348813, "gaming_main")
    plan = plan_music_timeline(
        video_duration_sec=528.348813,
        available_tracks=_tracks(count=4, duration=150.0),
        content_type="gaming_main",
        mood_timeline=mood["mood_timeline"],
    )

    _assert_covers_video(plan, 528.348813)
    assert plan["music_timeline_planner_enabled"] is True
    assert plan["track_duration_aware_selection"] is True
    assert plan["duration_based_song_count"] is True
    assert plan["selected_music_track_count"] >= 3
    assert plan["single_song_loop"] is False


def test_20_minute_video_uses_more_songs_than_8_8_minute_video():
    short_plan = plan_music_timeline(
        video_duration_sec=528.0,
        available_tracks=_tracks(count=8, duration=150.0),
        content_type="gaming_main",
    )
    long_plan = plan_music_timeline(
        video_duration_sec=1200.0,
        available_tracks=_tracks(count=8, duration=150.0),
        content_type="gaming_main",
    )

    assert long_plan["music_timeline_segment_count"] > short_plan["music_timeline_segment_count"]
    assert long_plan["music_timeline_segment_count"] >= 8


def test_30_minute_video_uses_more_segments_without_single_song_loop():
    plan = plan_music_timeline(
        video_duration_sec=1800.0,
        available_tracks=_tracks(count=10, duration=150.0),
        content_type="gaming_main",
    )

    _assert_covers_video(plan, 1800.0)
    assert plan["music_timeline_segment_count"] >= 12
    assert plan["single_song_loop"] is False


def test_track_duration_is_never_overused():
    plan = plan_music_timeline(
        video_duration_sec=300.0,
        available_tracks=_tracks(count=4, duration=90.0),
        content_type="gaming_main",
    )

    _assert_covers_video(plan, 300.0)
    assert all(segment["track_used_duration_sec"] <= 90.0 for segment in plan["music_timeline"])


def test_no_direct_repeat_when_alternatives_exist():
    plan = plan_music_timeline(
        video_duration_sec=600.0,
        available_tracks=_tracks(count=4, duration=90.0),
        content_type="gaming_main",
    )

    timeline = plan["music_timeline"]
    assert len(timeline) > 1
    for index in range(1, len(timeline)):
        assert timeline[index]["track_path"] != timeline[index - 1]["track_path"]
    assert plan["direct_repeat_found"] is False


def test_mood_category_mapping_for_gaming():
    assert mood_to_music_category(MOOD_FUNNY, "gaming_main") == MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND
    assert mood_to_music_category(MOOD_FAIL, "gaming_main") == MUSIC_CATEGORY_FAIL
    assert mood_to_music_category(MOOD_HYPE, "gaming_main") == MUSIC_CATEGORY_HYPE
    assert mood_to_music_category("epic", "gaming_main") == MUSIC_CATEGORY_HYPE
    assert mood_to_music_category(MOOD_SAD, "gaming_main") == MUSIC_CATEGORY_SAD

    mixed_tracks = (
        _tracks(MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND, count=2, duration=100.0)
        + _tracks(MUSIC_CATEGORY_FAIL, count=2, duration=100.0)
        + _tracks(MUSIC_CATEGORY_HYPE, count=2, duration=100.0)
        + _tracks(MUSIC_CATEGORY_SAD, count=2, duration=100.0)
        + _tracks(MUSIC_CATEGORY_VLOG_BACKGROUND, count=2, duration=100.0)
    )
    mood_timeline = [
        {"start_sec": 0.0, "end_sec": 100.0, "mood": MOOD_FUNNY},
        {"start_sec": 100.0, "end_sec": 200.0, "mood": MOOD_FAIL},
        {"start_sec": 200.0, "end_sec": 300.0, "mood": MOOD_HYPE},
        {"start_sec": 300.0, "end_sec": 400.0, "mood": MOOD_SAD},
    ]

    plan = plan_music_timeline(
        video_duration_sec=400.0,
        available_tracks=mixed_tracks,
        content_type="gaming_main",
        mood_timeline=mood_timeline,
    )

    assert MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND in plan["used_music_categories"]
    assert MUSIC_CATEGORY_FAIL in plan["used_music_categories"]
    assert MUSIC_CATEGORY_HYPE in plan["used_music_categories"]
    assert MUSIC_CATEGORY_SAD in plan["used_music_categories"]
    assert MUSIC_CATEGORY_VLOG_BACKGROUND not in plan["used_music_categories"]


def test_uncut_blocks_music():
    plan = plan_music_timeline(
        video_duration_sec=600.0,
        available_tracks=_tracks(count=4, duration=120.0),
        content_type="uncut",
    )

    assert plan["status"] == "blocked_uncut_no_music"
    assert plan["music_timeline"] == []
    assert plan["selected_music_track_count"] == 0


def test_adaptive_gain_clamps_and_differs_by_loudness():
    loud = compute_adaptive_track_gain(
        track_mean_volume_db=-9.0,
        reference_track_mean_volume_db=-20.0,
    )
    quiet = compute_adaptive_track_gain(
        track_mean_volume_db=-30.0,
        reference_track_mean_volume_db=-20.0,
    )

    assert -40.0 <= loud["final_gain_db"] <= -35.0
    assert -40.0 <= quiet["final_gain_db"] <= -35.0
    assert loud["final_gain_db"] != quiet["final_gain_db"]
    assert loud["final_gain_db"] < quiet["final_gain_db"]


def test_fallback_honestly_reports_no_true_ai_mood_detection():
    fallback = build_fallback_video_mood_timeline(528.0, "gaming_main")

    assert fallback["true_ai_mood_detection_used"] is False
    assert "fallback" in fallback["mood_analysis_source"]
    assert fallback["mood_timeline"]


def test_classify_music_track_category_uses_folder_name():
    path = Path("local_assets/music/main_account/hype/song.mp3")
    assert classify_music_track_category(path) == MUSIC_CATEGORY_HYPE
