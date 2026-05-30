from __future__ import annotations

from core.play_segment_boundary_detector import FORBIDDEN_CORE_TERMS, PlaySegmentBoundaryDetector, assert_neutral_taxonomy
from models.play_segment import (
    PLAY_SEGMENT_INTENSITIES,
    PLAY_SEGMENT_STATES,
    PlaySegment,
    PlaySignalWindow,
    active_vs_idle_menu_share,
    dominant_state,
    duration_by_state,
)


def test_g6_2_neutral_taxonomy_has_no_forbidden_game_or_sport_terms() -> None:
    assert_neutral_taxonomy()

    joined = " ".join(list(PLAY_SEGMENT_STATES) + list(PLAY_SEGMENT_INTENSITIES)).lower()
    for forbidden in FORBIDDEN_CORE_TERMS:
        assert forbidden not in joined


def test_g6_2_quiet_active_play_is_active_low_intensity_not_idle() -> None:
    detector = PlaySegmentBoundaryDetector(window_seconds=2.0)

    audio_metrics = {
        0: {"audio_activity": 0.30, "audio_peak_score": 0.12},
        1: {"audio_activity": 0.34, "audio_peak_score": 0.14},
        2: {"audio_activity": 0.31, "audio_peak_score": 0.10},
    }
    visual_metrics = {
        0: {
            "motion_score": 0.12,
            "scene_change_score": 0.10,
            "visual_stability": 0.90,
            "edge_stability": 0.86,
            "color_stability": 0.84,
            "visual_richness": 0.44,
        },
        1: {
            "motion_score": 0.15,
            "scene_change_score": 0.09,
            "visual_stability": 0.91,
            "edge_stability": 0.84,
            "color_stability": 0.83,
            "visual_richness": 0.42,
        },
        2: {
            "motion_score": 0.13,
            "scene_change_score": 0.11,
            "visual_stability": 0.89,
            "edge_stability": 0.85,
            "color_stability": 0.82,
            "visual_richness": 0.41,
        },
    }

    windows = detector._classify_windows(6.0, audio_metrics, visual_metrics)

    assert windows
    assert {window.state for window in windows} == {"active_play"}
    assert {window.intensity for window in windows} == {"low"}
    assert all(window.evidence["quiet_active_rule"] for window in windows)
    assert all(window.confidence >= 0.66 for window in windows)


def test_g6_2_consolidates_neighboring_equal_states_and_keeps_required_fields() -> None:
    detector = PlaySegmentBoundaryDetector(window_seconds=2.0)

    windows = [
        PlaySignalWindow(0.0, 2.0, 0.1, 0.05, 0.0, 0.0, 0.9, 0.9, 0.9, "intro_menu_lobby", "unknown", 0.7, {"x": 1}, []),
        PlaySignalWindow(2.0, 4.0, 0.1, 0.05, 0.0, 0.0, 0.9, 0.9, 0.9, "intro_menu_lobby", "unknown", 0.7, {"x": 1}, []),
        PlaySignalWindow(4.0, 6.0, 0.5, 0.5, 0.2, 0.1, 0.6, 0.6, 0.6, "active_play", "medium", 0.8, {"x": 2}, []),
        PlaySignalWindow(6.0, 8.0, 0.6, 0.5, 0.2, 0.1, 0.6, 0.6, 0.6, "active_play", "medium", 0.8, {"x": 2}, []),
    ]

    segments = detector._consolidate_windows(windows)

    assert len(segments) == 2
    assert segments[0].state == "intro_menu_lobby"
    assert segments[0].start_seconds == 0.0
    assert segments[0].end_seconds == 4.0
    assert segments[1].state == "active_play"
    assert segments[1].intensity == "medium"
    assert segments[1].source_signal_counts["windows"] == 2

    data = segments[1].to_dict()
    assert set(data) == {
        "start_seconds",
        "end_seconds",
        "duration_seconds",
        "state",
        "intensity",
        "confidence",
        "evidence",
        "source_signal_counts",
        "warnings",
    }


def test_g6_2_duration_helpers_support_lol_active_vs_idle_metric() -> None:
    segments = [
        PlaySegment(0.0, 10.0, "intro_menu_lobby", "unknown", 0.8),
        PlaySegment(10.0, 80.0, "active_play", "low", 0.8),
        PlaySegment(80.0, 90.0, "transition_dead_time", "unknown", 0.8),
        PlaySegment(90.0, 120.0, "active_play", "medium", 0.8),
    ]

    totals = duration_by_state(segments, 10.0, 120.0)
    assert totals["active_play"] == 100.0
    assert totals["transition_dead_time"] == 10.0
    assert dominant_state(segments, 10.0, 120.0) == "active_play"

    share = active_vs_idle_menu_share(
        segments,
        10.0,
        120.0,
        exclude_ranges=[{"start_seconds": 80.0, "end_seconds": 90.0}],
    )
    assert share["active_play_seconds"] == 100.0
    assert share["idle_menu_seconds"] == 0.0
    assert share["active_play_share"] == 1.0
