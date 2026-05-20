"""
P3-3B Wirkungsbeweis: Hook-Signal erhöht den Score des überlappenden Kandidaten.
Kein echter Pipeline-Lauf — minimaler synthetischer Setup.
"""

from types import SimpleNamespace

import pytest


def test_hook_signal_boosts_candidate_score():
    """
    Kandidat A überlappt Hook-Signal [5.0, 15.0].
    Kandidat B überlappt Hook-Signal NICHT.
    Mit aktivem Hook-Signal muss Score(A) > Score(A_ohne_hook).
    """
    pytest.importorskip(
        "core.longform_timeline_builder",
        reason="core module not importable",
    )
    from core.longform_timeline_builder import LongformTimelineBuilder
    from core.timeline_signal_consumer import (
        SIGNAL_HOOK_IDENTIFICATION,
        TimelineSignalConsumer,
    )

    job_with_hook = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_HOOK_IDENTIFICATION,
                "start_seconds": 5.0,
                "end_seconds": 15.0,
                "score": 1.0,
            }
        ]
    )
    job_without_hook = SimpleNamespace(unified_edit_signals=[])

    builder = LongformTimelineBuilder()

    overlapping_candidate = SimpleNamespace(
        candidate_id="candidate_hook_overlap",
        start_time=8.0,
        end_time=12.0,
        highlight_score=0.5,
        confidence=0.5,
        candidate_kind="speech_peak",
        signal_tags=[],
    )
    non_overlapping_candidate = SimpleNamespace(
        candidate_id="candidate_no_hook_overlap",
        start_time=20.0,
        end_time=24.0,
        highlight_score=0.5,
        confidence=0.5,
        candidate_kind="speech_peak",
        signal_tags=[],
    )

    consumer_with = TimelineSignalConsumer.from_job(job_with_hook)
    consumer_without = TimelineSignalConsumer.from_job(job_without_hook)

    score_with, notes_with = builder._score_candidate_for_longform(
        overlapping_candidate,
        [],
        consumer=consumer_with,
    )
    score_without, notes_without = builder._score_candidate_for_longform(
        overlapping_candidate,
        [],
        consumer=consumer_without,
    )
    score_non_overlap, notes_non_overlap = builder._score_candidate_for_longform(
        non_overlapping_candidate,
        [],
        consumer=consumer_with,
    )

    assert score_with > score_without, (
        f"Erwartet score_with ({score_with:.4f}) > score_without ({score_without:.4f})"
    )
    assert score_with > score_non_overlap, (
        f"Erwartet score_with ({score_with:.4f}) > score_non_overlap ({score_non_overlap:.4f})"
    )
    assert "hook_signal_boost" in notes_with
    assert "hook_signal_boost" not in notes_without
    assert "hook_signal_boost" not in notes_non_overlap
