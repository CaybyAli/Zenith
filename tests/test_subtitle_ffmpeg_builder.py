from __future__ import annotations

import re

from core.subtitle_ffmpeg_builder import SubtitleFFmpegBuilder, _resolve_font
from core.subtitle_generator import SubtitleSegment, SubtitleStyle
from models.transcript_result import TranscriptWord


def _timed_segment(words: list[TranscriptWord]) -> SubtitleSegment:
    segment = SubtitleSegment(
        text=" ".join(word.text for word in words),
        start=words[0].start_seconds,
        end=words[-1].end_seconds,
        highlight_words=[],
        style=SubtitleStyle(),
    )
    segment.words = words
    return segment


def test_highlight_does_not_overlap_with_base_in_time() -> None:
    segment = SubtitleSegment(
        text="Warum ist das so",
        start=0.0,
        end=4.0,
        highlight_words=["Warum"],
        style=SubtitleStyle(),
    )

    filter_string = SubtitleFFmpegBuilder.build_filter_string([segment])
    enable_ranges = [
        tuple(float(value) for value in match)
        for match in re.findall(
            r"enable='between\(t,([0-9.]+),([0-9.]+)\)'",
            filter_string,
        )
    ]

    assert len(enable_ranges) == 2

    base_start, base_end = enable_ranges[0]
    highlight_start, highlight_end = enable_ranges[1]
    mid = 2.0

    assert base_start == 0.0
    assert base_end <= mid
    assert highlight_start >= mid
    assert highlight_end == 4.0
    assert base_end <= highlight_start


def test_no_glued_words_in_filter() -> None:
    segments = [
        _timed_segment(
            [
                TranscriptWord(text="ES", start_seconds=0.0, end_seconds=0.5),
                TranscriptWord(text="NICHT", start_seconds=0.5, end_seconds=1.0),
            ]
        ),
        _timed_segment(
            [
                TranscriptWord(text="MUSST", start_seconds=1.0, end_seconds=1.5),
                TranscriptWord(text="AUCH", start_seconds=1.5, end_seconds=2.0),
            ]
        ),
    ]

    filter_string = SubtitleFFmpegBuilder.build_filter_string(segments)

    assert "ESNICHT" not in filter_string
    assert "MUSSTAUCH" not in filter_string
    assert "ES NICHT" in filter_string
    assert "MUSST AUCH" in filter_string


def test_font_fallback_returns_string() -> None:
    font = _resolve_font()

    assert isinstance(font, str)
    assert len(font) > 0
