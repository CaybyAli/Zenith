from __future__ import annotations

import pytest

from core.music_automation_planner import (
    DEFAULT_BASE_TARGET_GAIN_DB,
    MUSIC_AUDIBILITY_FLOOR_DB,
    MUSIC_LOUDNESS_CEILING_DB,
    OWNER_MUSIC_AUDIBLE_GAIN_RANGE_DB,
    build_analysis_windows,
    build_clean_transition_policy_for_track,
    build_music_automation_plan,
    compute_dynamic_music_gain,
    smooth_gain_curve,
)


def test_5s_windows_cover_full_video_without_gaps_or_overlap():
    windows = build_analysis_windows(528.348813, window_sec=5.0)

    assert len(windows) == 106
    assert windows[0] == {"start_sec": 0.0, "end_sec": 5.0}
    assert windows[-1]["end_sec"] == pytest.approx(528.349, abs=0.002)

    for previous, current in zip(windows, windows[1:]):
        assert previous["end_sec"] == pytest.approx(current["start_sec"], abs=0.001)
        assert previous["end_sec"] <= current["start_sec"] + 0.001


def test_voice_aware_gain_loud_voice_is_lower_than_quiet_voice():
    loud = compute_dynamic_music_gain(voice_level_db=-18.0, music_section_level_db=-30.0)
    quiet = compute_dynamic_music_gain(voice_level_db=-55.0, music_section_level_db=-30.0)

    assert loud["final_gain_db"] < quiet["final_gain_db"]
    assert MUSIC_AUDIBILITY_FLOOR_DB <= loud["final_gain_db"] <= -33.0
    assert -29.0 <= quiet["final_gain_db"] <= MUSIC_LOUDNESS_CEILING_DB
    assert loud["final_gain_db"] >= MUSIC_AUDIBILITY_FLOOR_DB


def test_music_section_loudness_changes_gain():
    loud_section = compute_dynamic_music_gain(voice_level_db=-36.0, music_section_level_db=-18.0)
    quiet_section = compute_dynamic_music_gain(voice_level_db=-36.0, music_section_level_db=-42.0)

    assert loud_section["final_gain_db"] < quiet_section["final_gain_db"]


def test_gain_clamp_keeps_all_final_gains_inside_owner_audible_range():
    plan = build_music_automation_plan(
        video_duration_sec=30.0,
        music_timeline=[],
        mixed_audio_levels_db=[-10.0, -50.0, -18.0, -55.0, -30.0, -40.0],
        music_section_levels_db=[-10.0, -50.0, -20.0, -42.0, -30.0, -36.0],
    )

    gains = [window["final_gain_db"] for window in plan["music_automation_plan"]]
    assert gains
    assert all(MUSIC_AUDIBILITY_FLOOR_DB <= gain <= MUSIC_LOUDNESS_CEILING_DB for gain in gains)
    assert plan["music_audibility_policy_enabled"] is True
    assert plan["owner_music_audible_gain_range_db"] == [-35.0, -26.0]
    assert plan["owner_music_target_gain_db"] == DEFAULT_BASE_TARGET_GAIN_DB
    assert plan["automation_all_final_gains_between_audible_range"] is True
    assert plan["automation_all_final_gains_between_minus_40_and_minus_35"] is False


def test_owner_review_music_not_audible_updates_gain_policy():
    assert OWNER_MUSIC_AUDIBLE_GAIN_RANGE_DB == (-35.0, -26.0)
    assert DEFAULT_BASE_TARGET_GAIN_DB == -30.0
    assert MUSIC_AUDIBILITY_FLOOR_DB == -35.0
    assert MUSIC_LOUDNESS_CEILING_DB == -26.0


def test_106_window_final_gains_are_audible_without_sticking_to_floor():
    plan = build_music_automation_plan(
        video_duration_sec=528.348813,
        music_timeline=[],
        mixed_audio_levels_db=[-50.0, -31.0, -18.0],
        music_section_levels_db=[-18.0, -30.0, -42.0],
    )

    gains = [window["final_gain_db"] for window in plan["music_automation_plan"]]
    average_gain = sum(gains) / len(gains)

    assert len(gains) == 106
    assert all(MUSIC_AUDIBILITY_FLOOR_DB <= gain <= MUSIC_LOUDNESS_CEILING_DB for gain in gains)
    assert -33.0 <= average_gain <= -28.0
    assert not all(gain <= -38.0 for gain in gains)
    assert not all(gain == MUSIC_AUDIBILITY_FLOOR_DB for gain in gains)


def test_smoothing_limits_gain_jumps_to_2db():
    windows = [
        {"start_sec": 0.0, "end_sec": 5.0, "raw_gain_db": -35.0, "final_gain_db": -35.0},
        {"start_sec": 5.0, "end_sec": 10.0, "raw_gain_db": -26.0, "final_gain_db": -26.0},
        {"start_sec": 10.0, "end_sec": 15.0, "raw_gain_db": -35.0, "final_gain_db": -35.0},
    ]

    smoothed = smooth_gain_curve(windows, max_delta_db=2.0)
    gains = [window["final_gain_db"] for window in smoothed]

    for previous, current in zip(gains, gains[1:]):
        assert abs(current - previous) <= 2.0


def test_ali_friend_separation_is_honest_without_separated_data():
    plan = build_music_automation_plan(
        video_duration_sec=10.0,
        music_timeline=[],
        mixed_audio_levels_db=[-32.0, -33.0],
    )

    assert plan["ali_friend_separation_confirmed"] is False
    assert plan["speaker_voice_source"] == "mixed_audio_level"


def test_clean_transition_policy_uses_intro_outro_trim_and_crossfade():
    policy = build_clean_transition_policy_for_track(150.0)

    assert policy["clean_transition_policy_enabled"] is True
    assert policy["track_start_trim_sec"] == 30.0
    assert policy["track_end_trim_sec"] == 15.0
    assert policy["crossfade_sec"] == 3.0
    assert policy["hard_cut_transitions"] is False
    assert policy["usable_start_sec"] == 30.0
    assert policy["usable_end_sec"] == 135.0


def test_short_track_has_safe_transition_fallback():
    policy = build_clean_transition_policy_for_track(40.0)

    assert policy["safe_trim_reduced"] is True
    assert policy["track_skipped"] is True
    assert policy["usable_start_sec"] == 0.0
    assert policy["usable_end_sec"] == 40.0
    assert policy["usable_duration_sec"] > 0.0


def test_no_render_safety_terms_in_automation_planner_source():
    source = __import__("pathlib").Path("core/music_automation_planner.py").read_text(encoding="utf-8")

    assert "shell=True" not in source
    assert "requests" not in source
    assert "while True" not in source
    assert "Remove-Item" not in source
