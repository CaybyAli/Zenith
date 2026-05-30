from __future__ import annotations

from core.active_play_engagement_classifier import (
    ActivePlayEngagementClassifier,
    assert_g7a_neutral_taxonomy,
)
from models.play_segment import PlaySegment, PlaySegmentDetectionResult, PlaySignalWindow


def _window(
    start: float,
    end: float,
    *,
    motion: float,
    audio: float,
    peak: float,
    scene: float,
    stability: float,
    richness: float,
    state: str = "active_play",
) -> PlaySignalWindow:
    return PlaySignalWindow(
        start_seconds=start,
        end_seconds=end,
        motion_score=motion,
        audio_activity=audio,
        audio_peak_score=peak,
        scene_change_score=scene,
        visual_stability=stability,
        edge_stability=1.0 if stability >= 0.98 else 0.5,
        color_stability=1.0 if stability >= 0.98 else 0.5,
        state=state,
        intensity="high" if motion >= 0.5 or audio >= 0.5 else "low",
        confidence=0.8,
        evidence={
            "visual_richness": richness,
            "active_score": 0.7 if state == "active_play" else 0.2,
            "idle_score": 0.2,
            "transition_score": 0.2,
        },
        warnings=[],
    )


def _result(windows: list[PlaySignalWindow], active_start: float = 0.0, active_end: float | None = None) -> PlaySegmentDetectionResult:
    active_end = active_end if active_end is not None else windows[-1].end_seconds
    segment = PlaySegment(
        start_seconds=active_start,
        end_seconds=active_end,
        state="active_play",
        intensity="high",
        confidence=0.9,
        evidence={},
        source_signal_counts={"windows": len(windows)},
        warnings=[],
    )
    return PlaySegmentDetectionResult(
        video_path="synthetic",
        video_duration_seconds=active_end,
        analyzed_duration_seconds=active_end,
        window_seconds=2.0,
        taxonomy=["intro_menu_lobby", "active_play", "transition_dead_time", "replay_break", "unknown"],
        intensity_values=["low", "medium", "high", "unknown"],
        raw_windows=windows,
        segments=[segment],
        review_candidates={},
        warnings=[],
    )


def test_g7a_taxonomy_has_no_forbidden_game_or_sport_terms() -> None:
    assert_g7a_neutral_taxonomy()


def test_g7a_sustained_low_signal_inside_active_context_is_trimmable() -> None:
    windows = [
        _window(i, i + 2, motion=0.08, audio=0.0, peak=0.0, scene=0.05, stability=0.94, richness=0.40)
        for i in range(0, 8, 2)
    ]
    result = _result(windows)

    classified = ActivePlayEngagementClassifier().classify(result)
    spans = [span.to_dict() for span in classified.spans]

    assert any(span["keep_recommendation"] == "trimmable_low_engagement" for span in spans)


def test_g7a_high_signal_window_is_keep_active_not_fake_low_engagement() -> None:
    windows = [
        _window(0, 2, motion=0.96, audio=0.97, peak=0.99, scene=0.82, stability=0.18, richness=0.94),
        _window(2, 4, motion=0.88, audio=0.84, peak=0.95, scene=0.70, stability=0.30, richness=0.90),
    ]
    result = _result(windows)

    classified = ActivePlayEngagementClassifier().classify(result)
    spans = [span.to_dict() for span in classified.spans]

    assert all(span["keep_recommendation"] == "keep_active" for span in spans)


def test_g7a_sustained_frozen_inside_active_context_is_frozen_or_paused() -> None:
    windows = [
        _window(0, 2, motion=0.0, audio=0.0, peak=0.0, scene=0.0, stability=1.0, richness=0.45),
        _window(2, 4, motion=0.0, audio=0.0, peak=0.0, scene=0.0, stability=1.0, richness=0.45),
        _window(4, 6, motion=0.0, audio=0.0, peak=0.0, scene=0.0, stability=1.0, richness=0.45),
    ]
    result = _result(windows, active_end=6.0)

    classified = ActivePlayEngagementClassifier().classify(result)
    spans = [span.to_dict() for span in classified.spans]

    assert any(span["keep_recommendation"] == "frozen_or_paused" for span in spans)


def test_g7a_short_low_signal_is_not_trimmed_without_sustained_duration() -> None:
    windows = [
        _window(0, 2, motion=0.05, audio=0.0, peak=0.0, scene=0.02, stability=0.95, richness=0.4),
        _window(2, 4, motion=0.95, audio=0.95, peak=0.95, scene=0.80, stability=0.20, richness=0.9),
    ]
    result = _result(windows)

    classified = ActivePlayEngagementClassifier().classify(result)
    spans = [span.to_dict() for span in classified.spans]

    assert all(span["keep_recommendation"] == "keep_active" for span in spans)
