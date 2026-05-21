"""
P3-3C Wirkungsbeweis: Emotional Arc Signal beeinflusst die Segment-Reihenfolge.
"""

from types import SimpleNamespace

import pytest

from core.timeline_signal_consumer import (
    SIGNAL_EMOTIONAL_ARC,
    TimelineSignalConsumer,
)


def test_arc_ordering_reorders_segments_by_phase():
    """
    Segmente mit Arc-Signalen werden nach Phase sortiert:
    climax-Segment vor hook-Segment -> nach Arc-Ordering: hook zuerst.
    """
    pytest.importorskip("core.longform_timeline_builder")
    from core.longform_timeline_builder import LongformTimelineBuilder

    seg_climax = SimpleNamespace(
        start_time=10.0,
        end_time=20.0,
        segment_id="climax_seg",
    )
    seg_hook = SimpleNamespace(
        start_time=30.0,
        end_time=40.0,
        segment_id="hook_seg",
    )
    seg_none = SimpleNamespace(
        start_time=50.0,
        end_time=60.0,
        segment_id="no_arc_seg",
    )

    job = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_EMOTIONAL_ARC,
                "start_seconds": 10.0,
                "end_seconds": 20.0,
                "arc_phase": "climax",
                "score": 0.9,
            },
            {
                "signal_type": SIGNAL_EMOTIONAL_ARC,
                "start_seconds": 30.0,
                "end_seconds": 40.0,
                "arc_phase": "hook",
                "score": 0.9,
            },
        ]
    )

    consumer = TimelineSignalConsumer.from_job(job)
    builder = LongformTimelineBuilder()

    original_order = [seg_climax, seg_hook, seg_none]
    reordered = builder._apply_arc_ordering(original_order, consumer)

    hook_pos = next(i for i, segment in enumerate(reordered) if segment.segment_id == "hook_seg")
    climax_pos = next(i for i, segment in enumerate(reordered) if segment.segment_id == "climax_seg")

    assert hook_pos < climax_pos, (
        f"hook_pos ({hook_pos}) sollte vor climax_pos ({climax_pos}) sein"
    )


def test_arc_ordering_with_no_consumer_returns_original():
    """Kein Consumer -> Original-Reihenfolge bleibt erhalten."""
    pytest.importorskip("core.longform_timeline_builder")
    from core.longform_timeline_builder import LongformTimelineBuilder

    segments = [
        SimpleNamespace(start_time=float(i), end_time=float(i + 5), segment_id=f"s{i}")
        for i in range(3)
    ]

    builder = LongformTimelineBuilder()
    result = builder._apply_arc_ordering(segments, None)

    assert [segment.segment_id for segment in result] == [
        segment.segment_id for segment in segments
    ]


def test_arc_ordering_with_no_signals_returns_original():
    """Keine Arc-Signale im Job -> Original-Reihenfolge bleibt erhalten."""
    pytest.importorskip("core.longform_timeline_builder")
    from core.longform_timeline_builder import LongformTimelineBuilder

    job = SimpleNamespace(unified_edit_signals=[])
    consumer = TimelineSignalConsumer.from_job(job)
    segments = [
        SimpleNamespace(start_time=float(i), end_time=float(i + 5), segment_id=f"s{i}")
        for i in range(3)
    ]

    builder = LongformTimelineBuilder()
    result = builder._apply_arc_ordering(segments, consumer)

    assert [segment.segment_id for segment in result] == [
        segment.segment_id for segment in segments
    ]
