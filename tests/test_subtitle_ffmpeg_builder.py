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


def _drawtext_clauses(filter_string: str) -> list[str]:
    if not filter_string:
        return []
    parts = filter_string.split(",drawtext=")
    return [parts[0], *[f"drawtext={part}" for part in parts[1:]]]


def _enable_range(clause: str) -> tuple[float, float]:
    match = re.search(r"enable='between\(t,([0-9.]+),([0-9.]+)\)'", clause)
    assert match is not None
    return float(match.group(1)), float(match.group(2))


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


def test_active_state_end_uses_next_word_start() -> None:
    segment = _timed_segment(
        [
            TranscriptWord(text="ES", start_seconds=0.0, end_seconds=0.2),
            TranscriptWord(text="NICHT", start_seconds=0.5, end_seconds=1.0),
        ]
    )

    filter_string = SubtitleFFmpegBuilder.build_filter_string([segment])
    active_es = next(
        clause
        for clause in _drawtext_clauses(filter_string)
        if "text='ES'" in clause and "fontcolor=#00FF38" in clause
    )

    assert _enable_range(active_es) == (0.0, 0.5)


def test_no_blank_timing_gap_between_adjacent_words() -> None:
    segment = _timed_segment(
        [
            TranscriptWord(text="ES", start_seconds=0.0, end_seconds=0.2),
            TranscriptWord(text="NICHT", start_seconds=0.5, end_seconds=1.0),
        ]
    )

    filter_string = SubtitleFFmpegBuilder.build_filter_string([segment])
    active_clauses = [
        clause
        for clause in _drawtext_clauses(filter_string)
        if "fontcolor=#00FF38" in clause
    ]
    active_ranges = [_enable_range(clause) for clause in active_clauses]

    assert active_ranges[0][1] == active_ranges[1][0]


def test_mobile_karaoke_font_size_is_equal_for_white_and_highlight() -> None:
    segment = _timed_segment(
        [
            TranscriptWord(text="ES", start_seconds=0.0, end_seconds=0.5),
            TranscriptWord(text="NICHT", start_seconds=0.5, end_seconds=1.0),
        ]
    )

    filter_string = SubtitleFFmpegBuilder.build_filter_string([segment])

    assert "fontcolor=white:fontsize=86" in filter_string
    assert "fontcolor=#00FF38:fontsize=86" in filter_string


def test_mobile_karaoke_uses_comic_y_position_and_border() -> None:
    segment = _timed_segment(
        [
            TranscriptWord(text="ES", start_seconds=0.0, end_seconds=0.5),
            TranscriptWord(text="NICHT", start_seconds=0.5, end_seconds=1.0),
        ]
    )

    filter_string = SubtitleFFmpegBuilder.build_filter_string([segment])

    assert "y=h*0.58" in filter_string
    assert "borderw=10" in filter_string


def test_font_fallback_returns_string() -> None:
    font = _resolve_font()

    assert isinstance(font, str)
    assert len(font) > 0


def test_escape_filter_value_windows_path_uses_forward_slashes() -> None:
    """Backslashes in Windows paths must become forward-slashes."""
    result = SubtitleFFmpegBuilder._escape_filter_value(
        r"D:\Zenith\assets\fonts\Bangers-Regular.ttf"
    )
    assert "\\" not in result.replace("\\:", ""), (
        f"Unexpected backslash in escaped path: {result!r}"
    )


def test_escape_filter_value_windows_drive_colon_is_escaped() -> None:
    """The drive-letter colon must be escaped as '\\:' for FFmpeg."""
    result = SubtitleFFmpegBuilder._escape_filter_value(
        r"D:\Zenith\assets\fonts\Bangers-Regular.ttf"
    )
    assert result.startswith("D\\:/"), (
        f"Drive colon not escaped correctly: {result!r}"
    )


def test_escape_filter_value_no_bare_colon_after_drive() -> None:
    """No unescaped colon must appear anywhere in the output."""
    result = SubtitleFFmpegBuilder._escape_filter_value(
        r"D:\Zenith\assets\fonts\Bangers-Regular.ttf"
    )
    without_escaped = result.replace("\\:", "")
    assert ":" not in without_escaped, (
        f"Bare colon found in escaped path: {result!r}"
    )


def test_escape_drawtext_text() -> None:
    assert SubtitleFFmpegBuilder._escape_drawtext_text("Hello:World") == "Hello\\:World"
    assert SubtitleFFmpegBuilder._escape_drawtext_text("It's") == "It\\'s"
    assert SubtitleFFmpegBuilder._escape_drawtext_text("[tag]") == "\\[tag\\]"
