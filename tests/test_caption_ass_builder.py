from __future__ import annotations

import re
from pathlib import Path

from core.caption_ass_builder import (
    ASS_DEFAULT_WHITE,
    ASS_HIGHLIGHT_GREEN,
    ASS_HIGHLIGHT_YELLOW,
    ASS_NORMAL_ACTIVE_SIZE,
    ASS_NORMAL_BASE_SIZE,
    ASS_OUTLINE_SIZE,
    ASS_SHORT_ACTIVE_SIZE,
    ASS_SHORT_BASE_SIZE,
    ASS_WORD_GAP,
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
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.startswith("Dialogue:")
    ]


def test_ass_header_valid_final_style(tmp_path: Path) -> None:
    output = tmp_path / "captions.ass"
    CaptionASSBuilder().generate_ass_file(
        [CaptionGroup(words=[_word("ich", 0.0, 0.3)])],
        str(output),
    )

    text = output.read_text(encoding="utf-8-sig")

    assert "[Script Info]" in text
    assert "PlayResX: 1080" in text
    assert "PlayResY: 1920" in text
    assert "WrapStyle: 1" in text
    assert f"Style: Default,Bangers,{ASS_NORMAL_BASE_SIZE}" in text
    assert f",1,{ASS_OUTLINE_SIZE},0,5," in text


def test_karaoke_timing_uses_final_delay_and_hold(tmp_path: Path) -> None:
    output = tmp_path / "captions.ass"
    CaptionASSBuilder().generate_ass_file(
        [
            CaptionGroup(
                words=[
                    _word("ich", 2.0, 2.3),
                    _word("hab", 2.3, 2.6),
                    _word("f?r", 2.6, 3.0),
                ]
            )
        ],
        str(output),
    )

    lines = _dialogue_lines(output)

    assert len(lines) == 3

    # Final D7: 0.12s text delay.
    assert "0:00:02.12,0:00:02.42" in lines[0]
    assert "0:00:02.42,0:00:02.72" in lines[1]

    # Last word holds briefly, with owner-confirmed 0.16s tail.
    assert "0:00:02.72,0:00:03.28" in lines[2]

    pattern = re.compile(r"Dialogue: 0,\d+:\d{2}:\d{2}\.\d{2},\d+:\d{2}:\d{2}\.\d{2},")
    assert all(pattern.match(line) for line in lines)


def test_color_code_correct_without_ass_reset(tmp_path: Path) -> None:
    output = tmp_path / "captions.ass"
    CaptionASSBuilder().generate_ass_file(
        [CaptionGroup(words=[_word("hab", 0.0, 0.4)])],
        str(output),
    )

    text = output.read_text(encoding="utf-8-sig")

    assert f"\\c{ASS_HIGHLIGHT_GREEN}" in text
    assert f"\\c{ASS_DEFAULT_WHITE}" in text

    # Final D7 uses explicit style restore, not {\\r}, because {\\r}
    # could reset font size/position unexpectedly.
    assert "{\\r}" not in text


def test_edge_cases_final_style(tmp_path: Path) -> None:
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
    assert f"\\fs{ASS_SHORT_BASE_SIZE}" in lines[0]
    assert f"\\fs{ASS_SHORT_ACTIVE_SIZE}" in lines[0]
    assert f"\\c{ASS_HIGHLIGHT_GREEN}" in lines[0]
    assert "{\\r}" not in lines[0]


def test_escape_ffmpeg_filter_path_windows_drive() -> None:
    assert escape_ffmpeg_filter_path(r"D:\Zenith\assets\fonts") == "D\\\\:/Zenith/assets/fonts"
    assert escape_ffmpeg_filter_path(Path(r"D:\Zenith\out\captions.ass")) == "D\\\\:/Zenith/out/captions.ass"


def test_preserves_german_umlauts(tmp_path: Path) -> None:
    output = tmp_path / "umlaut.ass"
    umlaut_word = "f" + chr(252) + "r"

    CaptionASSBuilder().generate_ass_file(
        [CaptionGroup(words=[_word(umlaut_word, 0.0, 0.4)])],
        str(output),
    )

    text = output.read_text(encoding="utf-8-sig")

    assert "F" + chr(220) + "R" in text
    assert "F?R" not in text
    assert "F\\U00FCR" not in text


def test_final_word_gap_and_center_position(tmp_path: Path) -> None:
    output = tmp_path / "gap.ass"
    CaptionASSBuilder().generate_ass_file(
        [
            CaptionGroup(
                words=[
                    _word("ich", 0.0, 0.2),
                    _word("bin", 0.2, 0.4),
                ]
            )
        ],
        str(output),
    )

    line = _dialogue_lines(output)[0]

    assert ASS_WORD_GAP in line
    assert r"{\an5\pos(540,1385)}" in line


def test_five_word_groups_are_repaired_to_no_five_word_caption() -> None:
    words = [
        _word("eins", 0.00, 0.10),
        _word("zwei", 0.14, 0.24),
        _word("drei", 0.28, 0.38),
        _word("vier", 0.42, 0.52),
        _word("f?nf", 0.56, 0.66),
    ]

    groups = CaptionASSBuilder().build_groups([CaptionGroup(words=words)])

    assert sum(len(group) for group in groups) == 5
    assert all(len(group) != 5 for group in groups)
    assert max(len(group) for group in groups) <= 3


def test_short_caption_uses_larger_short_sizes(tmp_path: Path) -> None:
    output = tmp_path / "short_size.ass"
    CaptionASSBuilder().generate_ass_file(
        [CaptionGroup(words=[_word("wow", 0.0, 0.4)])],
        str(output),
    )

    line = _dialogue_lines(output)[0]

    assert f"\\fs{ASS_SHORT_BASE_SIZE}" in line
    assert f"\\fs{ASS_SHORT_ACTIVE_SIZE}" in line
    assert f"\\fs{ASS_NORMAL_ACTIVE_SIZE}" not in line


def test_friend_discord_words_use_yellow_highlight(tmp_path: Path) -> None:
    output = tmp_path / "friend_yellow.ass"
    friend_word = TranscriptWord(
        text="discord",
        start_seconds=0.0,
        end_seconds=0.4,
        probability=0.9,
        speaker="friend",
        audio_track="discord",
    )

    CaptionASSBuilder().generate_ass_file(
        [CaptionGroup(words=[friend_word])],
        str(output),
    )

    text = output.read_text(encoding="utf-8-sig")
    assert f"\\c{ASS_HIGHLIGHT_YELLOW}" in text


def test_owner_and_friend_words_do_not_share_caption_group() -> None:
    owner_word = TranscriptWord(
        text="owner",
        start_seconds=0.0,
        end_seconds=0.3,
        probability=0.9,
        speaker="ali",
        audio_track="mic",
    )
    friend_word = TranscriptWord(
        text="discord",
        start_seconds=0.32,
        end_seconds=0.6,
        probability=0.9,
        speaker="friend",
        audio_track="discord",
    )

    groups = CaptionASSBuilder().build_groups(
        [CaptionGroup(words=[owner_word, friend_word])]
    )

    assert len(groups) == 2
    assert [word.audio_track for word in groups[0]] == ["mic"]
    assert [word.audio_track for word in groups[1]] == ["discord"]
