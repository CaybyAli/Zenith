from __future__ import annotations

from core.word_snap_2 import (
    apply_word_snap_2_to_segments,
    snap_edge_to_combined_vad_pause,
)


def test_word_snap_2_start_edge_inside_speech_snaps_to_speech_start():
    result = snap_edge_to_combined_vad_pause(
        edge_kind="start",
        old_edge_seconds=10.5,
        combined_speech_regions=[
            {"start_seconds": 10.0, "end_seconds": 12.0}
        ],
        snap_window_seconds=1.0,
    )

    assert result["status"] == "SNAPPED"
    assert result["new_seconds"] == 10.0
    assert result["delta_seconds"] == -0.5


def test_word_snap_2_end_edge_inside_speech_snaps_to_speech_end():
    result = snap_edge_to_combined_vad_pause(
        edge_kind="end",
        old_edge_seconds=11.5,
        combined_speech_regions=[
            {"start_seconds": 10.0, "end_seconds": 12.0}
        ],
        snap_window_seconds=1.0,
    )

    assert result["status"] == "SNAPPED"
    assert result["new_seconds"] == 12.0
    assert result["delta_seconds"] == 0.5


def test_word_snap_2_edge_at_pause_boundary_unchanged():
    result = snap_edge_to_combined_vad_pause(
        edge_kind="start",
        old_edge_seconds=10.0,
        combined_speech_regions=[
            {"start_seconds": 10.0, "end_seconds": 12.0}
        ],
        snap_window_seconds=1.0,
    )

    assert result["status"] == "UNCHANGED"
    assert result["new_seconds"] == 10.0


def test_word_snap_2_no_pause_in_window_leaves_residual():
    result = snap_edge_to_combined_vad_pause(
        edge_kind="start",
        old_edge_seconds=15.0,
        combined_speech_regions=[
            {"start_seconds": 10.0, "end_seconds": 20.0}
        ],
        snap_window_seconds=1.0,
    )

    assert result["status"] == "RESIDUAL"
    assert result["new_seconds"] == 15.0
    assert result["reason"] == "continuous_speech_no_pause_boundary_inside_snap_window"


def test_word_snap_2_does_not_bring_back_dead_air_trim():
    result = snap_edge_to_combined_vad_pause(
        edge_kind="start",
        old_edge_seconds=12.5,
        combined_speech_regions=[
            {"start_seconds": 12.0, "end_seconds": 15.0}
        ],
        dead_air_trims=[
            {"start_seconds": 12.1, "end_seconds": 12.4}
        ],
        snap_window_seconds=1.0,
    )

    assert result["status"] == "RESIDUAL"
    assert result["reason"] == "snap_would_bring_back_dead_air_2_trim"


def test_word_snap_2_apply_segments_updates_duration_and_audit():
    segments = [
        {
            "segment_id": "seg_001",
            "start_seconds": 10.5,
            "end_seconds": 19.5,
            "duration_seconds": 9.0,
        }
    ]

    output, audit = apply_word_snap_2_to_segments(
        plan_segments=segments,
        combined_speech_regions=[
            {"start_seconds": 10.0, "end_seconds": 12.0},
            {"start_seconds": 18.0, "end_seconds": 20.0},
        ],
        snap_window_seconds=1.0,
    )

    assert output[0]["start_seconds"] == 10.0
    assert output[0]["end_seconds"] == 20.0
    assert output[0]["duration_seconds"] == 10.0
    assert audit["snapped_edge_count"] == 2
    assert audit["residual_mid_speech_edge_count"] == 0
    assert audit["duration_delta_seconds"] == 1.0
