from __future__ import annotations

from core.caption_highlight_timing_nudge import apply_caption_highlight_timing_nudge_to_ass_text


def test_nudge_moves_full_visual_frame_when_one_line_has_active_highlight():
    ass = "\n".join(
        [
            "[Events]",
            "Dialogue: 0,0:00:07.94,0:00:08.22,Default,,0,0,0,,{\\an5}{\\fs180\\c&H00FFFFFF}{\\fs245\\c&H0000FF00&}SPIEL{\\fs180\\c&H00FFFFFF}\\h\\hJEDEN",
            "Dialogue: 0,0:00:07.94,0:00:08.22,Default,,0,0,0,,{\\an5}{\\fs180\\c&H00FFFFFF}ZWEITE\\h\\hZEILE",
            "Dialogue: 0,0:00:08.22,0:00:08.50,Default,,0,0,0,,{\\an5}{\\fs180\\c&H00FFFFFF}SPIEL\\h\\h{\\fs245\\c&H0000FF00&}JEDEN{\\fs180\\c&H00FFFFFF}",
        ]
    )

    result = apply_caption_highlight_timing_nudge_to_ass_text(ass, nudge_seconds=-0.10)

    assert "Dialogue: 0,0:00:07.84,0:00:08.12,Default,,0,0,0,,{\\an5}{\\fs180\\c&H00FFFFFF}{\\fs245\\c&H0000FF00&}SPIEL" in result
    assert "Dialogue: 0,0:00:07.84,0:00:08.12,Default,,0,0,0,,{\\an5}{\\fs180\\c&H00FFFFFF}ZWEITE" in result
    assert "Dialogue: 0,0:00:08.12,0:00:08.40,Default,,0,0,0,,{\\an5}{\\fs180\\c&H00FFFFFF}SPIEL" in result


def test_nudge_does_not_move_plain_non_active_time_group():
    ass = "\n".join(
        [
            "[Events]",
            "Dialogue: 0,0:00:07.94,0:00:08.22,Default,,0,0,0,,{\\an5}{\\fs180\\c&H00FFFFFF}SPIEL\\h\\hJEDEN",
        ]
    )

    result = apply_caption_highlight_timing_nudge_to_ass_text(ass, nudge_seconds=-0.10)

    assert "Dialogue: 0,0:00:07.94,0:00:08.22" in result


def test_nudge_clamps_frame_start_to_zero():
    ass = "\n".join(
        [
            "Dialogue: 0,0:00:00.05,0:00:00.20,Default,,0,0,0,,{\\fs245\\c&H0000FFFF&}JA{\\fs180\\c&H00FFFFFF}",
            "Dialogue: 0,0:00:00.05,0:00:00.20,Default,,0,0,0,,{\\fs180\\c&H00FFFFFF}BEGLEITZEILE",
        ]
    )

    result = apply_caption_highlight_timing_nudge_to_ass_text(ass, nudge_seconds=-0.10)

    assert "Dialogue: 0,0:00:00.00,0:00:00.10" in result
    assert "{\\fs180\\c&H00FFFFFF}BEGLEITZEILE" in result
