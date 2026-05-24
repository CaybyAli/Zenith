from __future__ import annotations

import re

from core.subtitle_ffmpeg_builder import SubtitleFFmpegBuilder
from core.subtitle_generator import SubtitleSegment, SubtitleStyle


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
