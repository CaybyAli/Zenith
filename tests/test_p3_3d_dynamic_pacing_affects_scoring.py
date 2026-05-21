"""
P3-3D Wirkungsbeweis: Dynamic Pacing Signal beeinflusst den Kandidaten-Score.
"""

from types import SimpleNamespace

import pytest

from core.timeline_signal_consumer import (
    SIGNAL_DYNAMIC_PACING,
    TimelineSignalConsumer,
)


def test_pacing_match_boosts_score():
    """Kandidat mit hohem pacing_match_score bekommt Bonus."""
    pytest.importorskip("core.longform_timeline_builder")
    from core.longform_timeline_builder import LongformTimelineBuilder

    job_with_pacing = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_DYNAMIC_PACING,
                "start_seconds": 5.0,
                "end_seconds": 15.0,
                "pacing_match_score": 0.9,
                "monotony_score": 0.0,
            }
        ]
    )
    job_without = SimpleNamespace(unified_edit_signals=[])

    builder = LongformTimelineBuilder()
    candidate = SimpleNamespace(
        candidate_id="pacing_test",
        start_time=8.0,
        end_time=12.0,
        highlight_score=0.5,
        confidence=0.5,
        candidate_kind="action_peak",
        signal_tags=[],
    )

    consumer_with = TimelineSignalConsumer.from_job(job_with_pacing)
    consumer_without = TimelineSignalConsumer.from_job(job_without)

    score_with, notes_with = builder._score_candidate_for_longform(
        candidate,
        [],
        consumer=consumer_with,
    )
    score_without, notes_without = builder._score_candidate_for_longform(
        candidate,
        [],
        consumer=consumer_without,
    )

    assert score_with > score_without, (
        f"Erwartet score_with ({score_with:.4f}) > score_without ({score_without:.4f})"
    )
    assert "pacing_match_bonus" in notes_with
    assert "pacing_match_bonus" not in notes_without


def test_monotony_penalty_reduces_score():
    """Kandidat mit hohem monotony_score bekommt Penalty."""
    pytest.importorskip("core.longform_timeline_builder")
    from core.longform_timeline_builder import LongformTimelineBuilder

    job_monotone = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_DYNAMIC_PACING,
                "start_seconds": 5.0,
                "end_seconds": 15.0,
                "pacing_match_score": 0.0,
                "monotony_score": 0.9,
            }
        ]
    )
    job_without = SimpleNamespace(unified_edit_signals=[])

    builder = LongformTimelineBuilder()
    candidate = SimpleNamespace(
        candidate_id="monotony_test",
        start_time=8.0,
        end_time=12.0,
        highlight_score=0.6,
        confidence=0.6,
        candidate_kind="speech_peak",
        signal_tags=[],
    )

    consumer_monotone = TimelineSignalConsumer.from_job(job_monotone)
    consumer_without = TimelineSignalConsumer.from_job(job_without)

    score_monotone, notes_monotone = builder._score_candidate_for_longform(
        candidate,
        [],
        consumer=consumer_monotone,
    )
    score_without, _ = builder._score_candidate_for_longform(
        candidate,
        [],
        consumer=consumer_without,
    )

    assert score_monotone < score_without, (
        f"Erwartet score_monotone ({score_monotone:.4f}) < score_without ({score_without:.4f})"
    )
    assert "monotony_penalty" in notes_monotone


def test_pacing_modifier_clamped_to_safe_range():
    """Pacing-Modifier ueberschreitet nie +/-0.08."""
    pytest.importorskip("core.longform_timeline_builder")
    from core.longform_timeline_builder import LongformTimelineBuilder

    job = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_DYNAMIC_PACING,
                "start_seconds": 0.0,
                "end_seconds": 100.0,
                "pacing_match_score": 1.0,
                "monotony_score": 0.0,
            },
            {
                "signal_type": SIGNAL_DYNAMIC_PACING,
                "start_seconds": 0.0,
                "end_seconds": 100.0,
                "pacing_match_score": 1.0,
                "monotony_score": 0.0,
            },
        ]
    )
    job_without = SimpleNamespace(unified_edit_signals=[])

    builder = LongformTimelineBuilder()
    candidate = SimpleNamespace(
        candidate_id="clamp_test",
        start_time=10.0,
        end_time=20.0,
        highlight_score=0.5,
        confidence=0.5,
        candidate_kind="action_peak",
        signal_tags=[],
    )

    consumer = TimelineSignalConsumer.from_job(job)
    consumer_without = TimelineSignalConsumer.from_job(job_without)

    score_with, _ = builder._score_candidate_for_longform(
        candidate,
        [],
        consumer=consumer,
    )
    score_without, _ = builder._score_candidate_for_longform(
        candidate,
        [],
        consumer=consumer_without,
    )

    diff = score_with - score_without
    assert diff <= 0.09, f"Pacing-Boost darf max ~0.08 sein, war: {diff:.4f}"
