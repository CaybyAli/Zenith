from __future__ import annotations

from core.dead_air_trim import apply_dead_air_trim


def _plan():
    return {
        "duration_contract": {"planned_output_duration_seconds": 20.0},
        "timeline_segments": [
            {
                "segment_id": "seg_active_001",
                "block_id": "block_001",
                "start_seconds": 0.0,
                "end_seconds": 20.0,
                "duration_seconds": 20.0,
                "state": "active_play",
                "segment_role": "active_play",
            }
        ],
    }


def test_silence_low_action_long_enough_is_trimmed():
    result = apply_dead_air_trim(
        _plan(),
        silence_gaps=[{"silence_gap_id": "g1", "start_seconds": 4.0, "end_seconds": 6.0}],
        speech_segments=[],
        g6_action_windows=[
            {"start_seconds": 0.0, "end_seconds": 2.0, "state": "active_play", "action_score": 0.7},
            {"start_seconds": 4.0, "end_seconds": 6.0, "state": "active_play", "action_score": 0.1},
            {"start_seconds": 8.0, "end_seconds": 10.0, "state": "active_play", "action_score": 0.8},
        ],
        min_dead_gap_seconds=1.5,
        edge_buffer_seconds=0.2,
        action_floor_percentile=50.0,
    )

    assert result["dead_air_1_audit"]["trim_count"] == 1
    trim = result["dead_air_1_trimmed_gaps"][0]
    assert trim["trim_start_seconds"] == 4.2
    assert trim["trim_end_seconds"] == 5.8
    assert result["dead_air_1_audit"]["anti_overcut_fail_count"] == 0
    assert result["dead_air_1_audit"]["removed_speech_seconds"] == 0.0


def test_silence_high_action_is_not_trimmed():
    result = apply_dead_air_trim(
        _plan(),
        silence_gaps=[{"silence_gap_id": "g1", "start_seconds": 4.0, "end_seconds": 6.0}],
        speech_segments=[],
        g6_action_windows=[
            {"start_seconds": 0.0, "end_seconds": 2.0, "state": "active_play", "action_score": 0.1},
            {"start_seconds": 4.0, "end_seconds": 6.0, "state": "active_play", "action_score": 0.9},
            {"start_seconds": 8.0, "end_seconds": 10.0, "state": "active_play", "action_score": 0.2},
        ],
        min_dead_gap_seconds=1.5,
        edge_buffer_seconds=0.2,
        action_floor_percentile=50.0,
    )

    assert result["dead_air_1_audit"]["trim_count"] == 0
    assert result["dead_air_1_audit"]["evaluations"][0]["reason"] == "action_above_adaptive_floor"


def test_short_pause_is_not_trimmed():
    result = apply_dead_air_trim(
        _plan(),
        silence_gaps=[{"silence_gap_id": "g1", "start_seconds": 4.0, "end_seconds": 5.0}],
        speech_segments=[],
        g6_action_windows=[
            {"start_seconds": 4.0, "end_seconds": 6.0, "state": "active_play", "action_score": 0.1},
        ],
        min_dead_gap_seconds=1.5,
        edge_buffer_seconds=0.2,
        action_floor_percentile=50.0,
    )

    assert result["dead_air_1_audit"]["trim_count"] == 0
    assert result["dead_air_1_audit"]["evaluations"][0]["reason"] == "below_min_dead_gap_seconds"


def test_speech_overlap_is_not_trimmed_even_if_gap_claims_silence():
    result = apply_dead_air_trim(
        _plan(),
        silence_gaps=[{"silence_gap_id": "g1", "start_seconds": 4.0, "end_seconds": 6.0}],
        speech_segments=[{"start_seconds": 4.5, "end_seconds": 5.0, "text": "do not cut me"}],
        g6_action_windows=[
            {"start_seconds": 4.0, "end_seconds": 6.0, "state": "active_play", "action_score": 0.1},
        ],
        min_dead_gap_seconds=1.5,
        edge_buffer_seconds=0.2,
        action_floor_percentile=50.0,
    )

    assert result["dead_air_1_audit"]["trim_count"] == 0
    assert result["dead_air_1_audit"]["evaluations"][0]["reason"] == "speech_overlap_safety_block"
