from __future__ import annotations

import re

import pytest

from core.subtitle_ffmpeg_builder import (
    MOBILE_FIRST_BORDER_WIDTH,
    MOBILE_FIRST_CAPTION_CENTER_X,
    MOBILE_FIRST_CHAR_WIDTH_FACTOR,
    MOBILE_FIRST_FONT_SIZE,
    MOBILE_FIRST_LINE1_Y,
    MOBILE_FIRST_LINE2_Y,
    MOBILE_FIRST_SAFE_MARGIN_PX,
    MOBILE_FIRST_WORD_GAP_PX,
    SubtitleFFmpegBuilder,
    _resolve_font,
)
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


def _drawtext_option(clause: str, name: str) -> str:
    match = re.search(rf"(?:^|:){name}=([^:]+)", clause)
    assert match is not None
    return match.group(1)


def _layout_words(values: list[str]) -> list[dict[str, float | str]]:
    return [
        {
            "text": value,
            "start": float(index) * 0.2,
            "end": (float(index) * 0.2) + 0.2,
        }
        for index, value in enumerate(values)
    ]


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

    assert "y=h*0.62" in filter_string
    assert "borderw=10" in filter_string


def test_mobile_word_gap_uses_configured_gap_without_border_padding() -> None:
    layout = SubtitleFFmpegBuilder._mobile_word_layout(_layout_words(["AA", "BB"]))
    expected_offset = (
        len("AA") * MOBILE_FIRST_FONT_SIZE * MOBILE_FIRST_CHAR_WIDTH_FACTOR
        + MOBILE_FIRST_WORD_GAP_PX
    )
    border_padded_offset = expected_offset + (MOBILE_FIRST_BORDER_WIDTH * 2)

    assert layout[1]["offset"] == pytest.approx(expected_offset)
    assert layout[1]["offset"] != pytest.approx(border_padded_offset)


def test_mobile_long_group_splits_into_two_centered_lines() -> None:
    layout = SubtitleFFmpegBuilder._mobile_word_layout(
        _layout_words(["DU", "MUSST", "AUCH", "DATEN"])
    )

    assert [item["line_index"] for item in layout] == [0, 0, 1, 1]
    first_line_block_widths = {item["block_width"] for item in layout[:2]}
    second_line_block_widths = {item["block_width"] for item in layout[2:]}

    assert len(first_line_block_widths) == 1
    assert len(second_line_block_widths) == 1
    assert first_line_block_widths != second_line_block_widths
    assert [item["y"] for item in layout] == [
        MOBILE_FIRST_LINE1_Y,
        MOBILE_FIRST_LINE1_Y,
        MOBILE_FIRST_LINE2_Y,
        MOBILE_FIRST_LINE2_Y,
    ]
    assert all("max(64,min((w/2)-(" in str(item["x"]) for item in layout)


def test_mobile_overwide_three_word_group_splits_into_two_lines() -> None:
    layout = SubtitleFFmpegBuilder._mobile_word_layout(
        _layout_words(["ANALYSIEREN", "KOMPLETT", "JA."])
    )

    assert [item["line_index"] for item in layout] == [0, 1, 1]


def test_mobile_default_center_uses_screen_center_not_side_by_side_center() -> None:
    assert MOBILE_FIRST_CAPTION_CENTER_X == "w*0.50"
    assert MOBILE_FIRST_CAPTION_CENTER_X != "w*0.64"


def test_mobile_block_uses_safe_center_x_expression() -> None:
    filter_string = SubtitleFFmpegBuilder.build_filter_string(
        [
            _timed_segment(
                [
                    TranscriptWord(text="ES", start_seconds=0.0, end_seconds=0.5),
                    TranscriptWord(text="NICHT", start_seconds=0.5, end_seconds=1.0),
                ]
            )
        ]
    )

    assert "w*0.64" not in filter_string
    assert f"max({MOBILE_FIRST_SAFE_MARGIN_PX},min(" in filter_string
    assert f"w-text_w-{MOBILE_FIRST_SAFE_MARGIN_PX}" in filter_string


def test_mobile_word_layout_has_no_huge_gap_between_words() -> None:
    layout = SubtitleFFmpegBuilder._mobile_word_layout(_layout_words(["A", "B", "C"]))

    for previous, current in zip(layout, layout[1:]):
        gap = (
            float(current["offset"])
            - float(previous["offset"])
            - float(previous["width"])
        )
        assert gap == pytest.approx(MOBILE_FIRST_WORD_GAP_PX)
        assert 10 <= gap <= 14


def test_mobile_karaoke_timed_word_layers_disable_fix_bounds() -> None:
    segment = _timed_segment(
        [
            TranscriptWord(text="ES", start_seconds=0.0, end_seconds=0.5),
            TranscriptWord(text="NICHT", start_seconds=0.5, end_seconds=1.0),
        ]
    )

    filter_string = SubtitleFFmpegBuilder.build_filter_string([segment])
    timed_word_clauses = [
        clause
        for clause in _drawtext_clauses(filter_string)
        if "enable='between(t" in clause
    ]

    assert timed_word_clauses
    assert all("fix_bounds=0" in clause for clause in timed_word_clauses)
    assert all("fix_bounds=1" not in clause for clause in timed_word_clauses)


def test_active_word_color_changes_without_position_jumps() -> None:
    segment = _timed_segment(
        [
            TranscriptWord(text="ES", start_seconds=0.0, end_seconds=0.5),
            TranscriptWord(text="NICHT", start_seconds=0.5, end_seconds=1.0),
        ]
    )

    filter_string = SubtitleFFmpegBuilder.build_filter_string([segment])
    es_positions_by_color: dict[str, set[tuple[str, str]]] = {
        "white": set(),
        "highlight": set(),
    }
    for clause in _drawtext_clauses(filter_string):
        if not re.search(r"drawtext=text='ES':", clause):
            continue
        position = (_drawtext_option(clause, "x"), _drawtext_option(clause, "y"))
        if "fontcolor=#00FF38" in clause:
            es_positions_by_color["highlight"].add(position)
        elif "fontcolor=white" in clause:
            es_positions_by_color["white"].add(position)

    assert es_positions_by_color["highlight"]
    assert es_positions_by_color["white"]
    assert es_positions_by_color["highlight"] == es_positions_by_color["white"]


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
