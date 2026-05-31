from __future__ import annotations

from core.word_snap_2 import (
    apply_word_snap_2_fix_to_residuals,
    find_inner_word_boundary_fallback,
    normalize_speech_1_words,
)


def test_word_snap_2_fix_residual_start_to_reliable_word_start():
    result = find_inner_word_boundary_fallback(
        edge_kind="start",
        old_edge_seconds=10.45,
        speech_1_words=[
            {"word": "hallo", "start_seconds": 10.2, "end_seconds": 10.8},
        ],
        snap_window_seconds=1.0,
        max_word_seconds=1.2,
    )

    assert result["status"] == "WORD_BOUNDARY_SNAPPED"
    assert result["new_seconds"] == 10.2
    assert result["selected_word"]["word"] == "hallo"


def test_word_snap_2_fix_residual_end_to_reliable_word_end():
    result = find_inner_word_boundary_fallback(
        edge_kind="end",
        old_edge_seconds=10.45,
        speech_1_words=[
            {"word": "hallo", "start_seconds": 10.2, "end_seconds": 10.8},
        ],
        snap_window_seconds=1.0,
        max_word_seconds=1.2,
    )

    assert result["status"] == "WORD_BOUNDARY_SNAPPED"
    assert result["new_seconds"] == 10.8
    assert result["selected_word"]["word"] == "hallo"


def test_word_snap_2_fix_excludes_stretched_word():
    result = find_inner_word_boundary_fallback(
        edge_kind="start",
        old_edge_seconds=15.0,
        speech_1_words=[
            {"word": "richtig", "start_seconds": 10.0, "end_seconds": 20.0},
        ],
        snap_window_seconds=1.0,
        max_word_seconds=1.2,
    )

    assert result["status"] == "REAL_RESIDUAL"
    assert result["reason"] == "no_reliable_inner_word_boundary_inside_snap_window"
    assert result["stretched_words_near_edge"][0]["word"] == "richtig"


def test_word_snap_2_fix_no_word_boundary_stays_real_residual():
    result = find_inner_word_boundary_fallback(
        edge_kind="end",
        old_edge_seconds=50.0,
        speech_1_words=[
            {"word": "weitweg", "start_seconds": 60.0, "end_seconds": 60.5},
        ],
        snap_window_seconds=1.0,
        max_word_seconds=1.2,
    )

    assert result["status"] == "REAL_RESIDUAL"


def test_word_snap_2_fix_apply_updates_only_continuous_residual():
    segments = [
        {
            "segment_id": "seg_001",
            "start_seconds": 10.45,
            "end_seconds": 20.0,
            "duration_seconds": 9.55,
        }
    ]
    residuals = [
        {
            "segment_id": "seg_001",
            "edge_kind": "start",
            "old_seconds": 10.45,
            "reason": "continuous_speech_no_pause_boundary_inside_snap_window",
        }
    ]
    words = normalize_speech_1_words(
        [
            {"word": "hallo", "start_seconds": 10.2, "end_seconds": 10.8},
        ],
        max_word_seconds=1.2,
    )

    output, audit = apply_word_snap_2_fix_to_residuals(
        plan_segments=segments,
        residuals=residuals,
        speech_1_words=words,
        snap_window_seconds=1.0,
        max_word_seconds=1.2,
    )

    assert output[0]["start_seconds"] == 10.2
    assert audit["word_boundary_snapped_count"] == 1
    assert audit["real_residual_count"] == 0
    assert audit["stretched_word_snap_target_count"] == 0


def test_word_snap_2_fix_dead_air_trim_overlap_rejected():
    result = find_inner_word_boundary_fallback(
        edge_kind="start",
        old_edge_seconds=10.45,
        speech_1_words=[
            {"word": "hallo", "start_seconds": 10.2, "end_seconds": 10.8},
        ],
        dead_air_trims=[
            {"start_seconds": 10.25, "end_seconds": 10.35},
        ],
        snap_window_seconds=1.0,
        max_word_seconds=1.2,
    )

    assert result["status"] == "REAL_RESIDUAL"
    assert result["reason"] == "inner_word_snap_would_bring_back_dead_air_2_trim"
