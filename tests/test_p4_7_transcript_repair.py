from __future__ import annotations

from types import SimpleNamespace

from scripts.p4_7_4_rerun_transcripts import _first_text, transcript_ok


def test_first_text_falls_back_to_first_spoken_segments_when_opening_silent() -> None:
    segments = [
        SimpleNamespace(start=14.0, text="Erster gesprochener Satz nach Intro."),
        SimpleNamespace(start=19.0, text="Zweiter Satz mit Kontext."),
    ]

    count, first_text = _first_text(segments, first_seconds=10.0)

    assert count == 2
    assert first_text.startswith("Erster gesprochener Satz")


def test_transcript_ok_requires_language_segments_and_text() -> None:
    assert transcript_ok(
        {
            "transcript": {
                "language": "de",
                "segments_count": 6,
                "first_10s_text": "Das ist lang genug.",
            }
        }
    )
    assert not transcript_ok(
        {
            "transcript": {
                "language": "unknown",
                "segments_count": 6,
                "first_10s_text": "Das ist lang genug.",
            }
        }
    )
