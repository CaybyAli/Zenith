from types import SimpleNamespace

from core.timeline_signal_consumer import (
    SIGNAL_BUT_THEREFORE,
    SIGNAL_DYNAMIC_PACING,
    SIGNAL_EMOTIONAL_ARC,
    SIGNAL_FINAL_QUALITY,
    SIGNAL_HOOK_IDENTIFICATION,
    SIGNAL_REACTION_SHOT,
    TimelineSignalConsumer,
)


def test_from_job_without_signals_does_not_crash():
    """Job ohne unified_edit_signals crasht nicht."""
    job = SimpleNamespace()

    consumer = TimelineSignalConsumer.from_job(job)

    assert consumer.read(SIGNAL_HOOK_IDENTIFICATION).available is False


def test_from_job_with_wrong_format_does_not_crash():
    """Job mit kaputtem Signalformat crasht nicht."""
    job = SimpleNamespace(unified_edit_signals="kaputt")

    consumer = TimelineSignalConsumer.from_job(job)

    bundle = consumer.read(SIGNAL_HOOK_IDENTIFICATION)
    assert bundle.available is False
    assert bundle.signals == []


def test_read_returns_available_false_for_missing_signal():
    """Fehlendes Signal -> available=False, leere Liste, warning."""
    job = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_DYNAMIC_PACING,
                "score": 0.9,
            }
        ]
    )

    consumer = TimelineSignalConsumer.from_job(job)
    bundle = consumer.read(SIGNAL_HOOK_IDENTIFICATION)

    assert bundle.available is False
    assert bundle.signals == []
    assert bundle.warnings


def test_read_returns_available_true_for_existing_signal():
    """Vorhandenes Signal -> available=True, signals nicht leer."""
    job = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_HOOK_IDENTIFICATION,
                "score": 0.8,
            }
        ]
    )

    consumer = TimelineSignalConsumer.from_job(job)
    bundle = consumer.read(SIGNAL_HOOK_IDENTIFICATION)

    assert bundle.available is True
    assert bundle.signals


def test_signals_for_segment_uses_overlap_not_exact_match():
    """Ueberlappung [5.0, 10.0] trifft Signal [4.0, 6.0] -> wird zurueckgegeben."""
    job = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_HOOK_IDENTIFICATION,
                "start_seconds": 4.0,
                "end_seconds": 6.0,
                "score": 0.75,
            }
        ]
    )

    consumer = TimelineSignalConsumer.from_job(job)
    signals = consumer.signals_for_segment(5.0, 10.0, SIGNAL_HOOK_IDENTIFICATION)

    assert len(signals) == 1


def test_best_score_for_segment_returns_zero_when_no_signals():
    """Kein Signal -> 0.0, kein Crash."""
    job = SimpleNamespace(unified_edit_signals=[])

    consumer = TimelineSignalConsumer.from_job(job)

    assert consumer.best_score_for_segment(5.0, 10.0, SIGNAL_HOOK_IDENTIFICATION) == 0.0


def test_best_score_handles_missing_score_field():
    """Signal ohne Score-Feld -> 0.0, kein Crash."""
    job = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_HOOK_IDENTIFICATION,
                "start_seconds": 5.0,
                "end_seconds": 8.0,
            }
        ]
    )

    consumer = TimelineSignalConsumer.from_job(job)

    assert consumer.best_score_for_segment(5.0, 10.0, SIGNAL_HOOK_IDENTIFICATION) == 0.0


def test_best_score_uses_supported_score_fields():
    """Signal-Score-Felder werden sicher gelesen."""
    job = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_BUT_THEREFORE,
                "start_seconds": 1.0,
                "end_seconds": 4.0,
                "story_score": 0.66,
            },
            {
                "signal_type": SIGNAL_BUT_THEREFORE,
                "start_seconds": 2.0,
                "end_seconds": 5.0,
                "signal_score": 0.88,
            },
        ]
    )

    consumer = TimelineSignalConsumer.from_job(job)

    assert consumer.best_score_for_segment(3.0, 6.0, SIGNAL_BUT_THEREFORE) == 0.88


def test_signal_without_timestamps_is_not_filtered_out():
    """Signal ohne Zeitstempel wird trotzdem zurueckgegeben."""
    job = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_EMOTIONAL_ARC,
                "score": 0.5,
            }
        ]
    )

    consumer = TimelineSignalConsumer.from_job(job)
    signals = consumer.signals_for_segment(10.0, 20.0, SIGNAL_EMOTIONAL_ARC)

    assert len(signals) == 1


def test_all_signal_constants_are_importable():
    """Alle freigegebenen Signal-Konstanten sind importierbar."""
    assert SIGNAL_HOOK_IDENTIFICATION
    assert SIGNAL_EMOTIONAL_ARC
    assert SIGNAL_DYNAMIC_PACING
    assert SIGNAL_REACTION_SHOT
    assert SIGNAL_BUT_THEREFORE
    assert SIGNAL_FINAL_QUALITY
