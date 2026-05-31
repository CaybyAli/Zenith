from __future__ import annotations

from core.dead_air_trim import (
    dead_air_2_apply_trims_to_segments,
    dead_air_2_normalize_action_windows,
    dead_air_2_normalize_intervals,
    dead_air_2_select_trims,
)


def _active_segment(start: float = 10.0, end: float = 20.0) -> dict:
    return {
        "segment_id": "seg_001",
        "start_seconds": start,
        "end_seconds": end,
        "duration_seconds": end - start,
        "metadata": {"state": "active_play"},
    }


def test_dead_air_2_trims_combined_silence_when_low_action():
    result = dead_air_2_select_trims(
        plan_segments=[_active_segment()],
        combined_silence_gaps=[
            {"start_seconds": 12.0, "end_seconds": 16.0, "duration_seconds": 4.0}
        ],
        action_windows=dead_air_2_normalize_action_windows([
            {"start_seconds": 12.0, "end_seconds": 16.0, "action_score": 0.1},
            {"start_seconds": 30.0, "end_seconds": 40.0, "action_score": 0.9},
        ]),
        combined_speech_regions=[],
        friend_only_regions=[],
        min_dead_gap_seconds=1.5,
        edge_buffer_seconds=0.2,
    )

    assert result["audit"]["trim_count"] == 1
    assert result["trims"][0]["start_seconds"] == 12.2
    assert result["trims"][0]["end_seconds"] == 15.8


def test_dead_air_2_friend_only_speech_is_protected():
    result = dead_air_2_select_trims(
        plan_segments=[_active_segment()],
        combined_silence_gaps=[
            {"start_seconds": 12.0, "end_seconds": 16.0, "duration_seconds": 4.0}
        ],
        action_windows=dead_air_2_normalize_action_windows([
            {"start_seconds": 12.0, "end_seconds": 16.0, "action_score": 0.1},
            {"start_seconds": 30.0, "end_seconds": 40.0, "action_score": 0.9},
        ]),
        combined_speech_regions=[],
        friend_only_regions=[
            {"start_seconds": 12.5, "end_seconds": 13.5, "duration_seconds": 1.0}
        ],
        min_dead_gap_seconds=1.5,
        edge_buffer_seconds=0.2,
    )

    assert result["audit"]["trim_count"] == 0
    assert any(item["reason"] == "friend_only_speech_protected" for item in result["rejected"])


def test_dead_air_2_combined_speech_overlap_is_rejected():
    result = dead_air_2_select_trims(
        plan_segments=[_active_segment()],
        combined_silence_gaps=[
            {"start_seconds": 12.0, "end_seconds": 16.0, "duration_seconds": 4.0}
        ],
        action_windows=dead_air_2_normalize_action_windows([
            {"start_seconds": 12.0, "end_seconds": 16.0, "action_score": 0.1},
            {"start_seconds": 30.0, "end_seconds": 40.0, "action_score": 0.9},
        ]),
        combined_speech_regions=[
            {"start_seconds": 14.0, "end_seconds": 14.5, "duration_seconds": 0.5}
        ],
        friend_only_regions=[],
        min_dead_gap_seconds=1.5,
        edge_buffer_seconds=0.2,
    )

    assert result["audit"]["trim_count"] == 0
    assert any(item["reason"] == "combined_speech_overlap" for item in result["rejected"])


def test_dead_air_2_high_action_is_rejected():
    result = dead_air_2_select_trims(
        plan_segments=[_active_segment()],
        combined_silence_gaps=[
            {"start_seconds": 12.0, "end_seconds": 16.0, "duration_seconds": 4.0}
        ],
        action_windows=dead_air_2_normalize_action_windows([
            {"start_seconds": 12.0, "end_seconds": 16.0, "action_score": 0.9},
            {"start_seconds": 30.0, "end_seconds": 40.0, "action_score": 0.1},
            {"start_seconds": 50.0, "end_seconds": 60.0, "action_score": 0.2},
        ]),
        combined_speech_regions=[],
        friend_only_regions=[],
        min_dead_gap_seconds=1.5,
        edge_buffer_seconds=0.2,
    )

    assert result["audit"]["trim_count"] == 0
    assert any(item["reason"] == "high_action" for item in result["rejected"])


def test_dead_air_2_apply_trims_splits_segment():
    segments = [_active_segment(10.0, 20.0)]
    trims = [
        {
            "segment_index": 0,
            "start_seconds": 12.0,
            "end_seconds": 14.0,
            "duration_seconds": 2.0,
        }
    ]

    output, duration = dead_air_2_apply_trims_to_segments(
        plan_segments=segments,
        trims=trims,
    )

    assert len(output) == 2
    assert output[0]["start_seconds"] == 10.0
    assert output[0]["end_seconds"] == 12.0
    assert output[1]["start_seconds"] == 14.0
    assert output[1]["end_seconds"] == 20.0
    assert duration == 8.0
