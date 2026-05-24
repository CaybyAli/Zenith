from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.caption_ass_builder import (
    ASS_HIGHLIGHT_GREEN,
    CaptionASSBuilder,
    CaptionGroup,
    escape_ffmpeg_filter_path,
)
from models.transcript_result import TranscriptWord


def _word(text: str, start: float, end: float) -> TranscriptWord:
    return TranscriptWord(
        text=text,
        start_seconds=start,
        end_seconds=end,
        probability=0.9,
    )


def _dialogue_lines(path: Path) -> list[str]:
    return [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("Dialogue:")
    ]


def test_ass_header_valid(tmp_path: Path) -> None:
    output = tmp_path / "captions.ass"
    CaptionASSBuilder().generate_ass_file(
        [CaptionGroup(words=[_word("ich", 0.0, 0.3)])],
        str(output),
    )

    text = output.read_text(encoding="utf-8")

    assert "[Script Info]" in text
    assert "PlayResX: 1080" in text
    assert "PlayResY: 1920" in text
    assert "Style: Default,Bangers" in text


def test_karaoke_timing(tmp_path: Path) -> None:
    output = tmp_path / "captions.ass"
    CaptionASSBuilder().generate_ass_file(
        [
            CaptionGroup(
                words=[
                    _word("ich", 2.0, 2.3),
                    _word("hab", 2.3, 2.6),
                    _word("für", 2.6, 3.0),
                ]
            )
        ],
        str(output),
    )

    lines = _dialogue_lines(output)

    assert len(lines) == 3
    assert "0:00:02.00,0:00:02.30" in lines[0]
    assert "0:00:02.30,0:00:02.60" in lines[1]
    assert "0:00:02.60,0:00:03.00" in lines[2]

    pattern = re.compile(r"Dialogue: 0,\d+:\d{2}:\d{2}\.\d{2},\d+:\d{2}:\d{2}\.\d{2},")
    assert all(pattern.match(line) for line in lines)


def test_color_code_correct(tmp_path: Path) -> None:
    output = tmp_path / "captions.ass"
    CaptionASSBuilder().generate_ass_file(
        [CaptionGroup(words=[_word("hab", 0.0, 0.4)])],
        str(output),
    )

    text = output.read_text(encoding="utf-8")

    assert f"\\c{ASS_HIGHLIGHT_GREEN}" in text
    assert "{\\r}" in text


def test_edge_cases(tmp_path: Path) -> None:
    empty_output = tmp_path / "empty.ass"
    CaptionASSBuilder().generate_ass_file(
        [CaptionGroup(words=[])],
        str(empty_output),
    )
    assert _dialogue_lines(empty_output) == []

    single_output = tmp_path / "single.ass"
    CaptionASSBuilder().generate_ass_file(
        [CaptionGroup(words=[_word("guck,", 0.0, 0.5)])],
        str(single_output),
    )

    lines = _dialogue_lines(single_output)

    assert len(lines) == 1
    assert "GUCK," in lines[0]
    assert f"\\c{ASS_HIGHLIGHT_GREEN}" in lines[0]
    assert "{\\r}" in lines[0]


def test_escape_ffmpeg_filter_path_windows_drive() -> None:
    assert escape_ffmpeg_filter_path(r"D:\Zenith\assets\fonts") == "D\\\\:/Zenith/assets/fonts"
    assert escape_ffmpeg_filter_path(Path(r"D:\Zenith\out\captions.ass")) == "D\\\\:/Zenith/out/captions.ass"

def test_preserves_german_umlauts(tmp_path: Path) -> None:
    output = tmp_path / "umlaut.ass"
    CaptionASSBuilder().generate_ass_file(
        [CaptionGroup(words=[_word("für", 0.0, 0.4)])],
        str(output),
    )

    text = output.read_text(encoding="utf-8-sig")

    assert "FÜR" in text
    assert "F?R" not in text
