from __future__ import annotations

import re
from collections import defaultdict

from core.caption_transcription_config import resolve_caption_highlight_timing_nudge_seconds


_ACTIVE_HIGHLIGHT_TAG_RE = re.compile(
    r"\{[^}]*\\fs(?:225|245)[^}]*\\c&H0000(?:FF00|FFFF)&[^}]*\}",
    re.IGNORECASE,
)


def _ass_time_to_seconds(value: str) -> float:
    h, m, rest = value.strip().split(":")
    s, cs = rest.split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100.0


def _seconds_to_ass_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    seconds -= h * 3600
    m = int(seconds // 60)
    seconds -= m * 60
    s = int(seconds)
    cs = int(round((seconds - s) * 100))

    if cs >= 100:
        s += 1
        cs -= 100
    if s >= 60:
        m += 1
        s -= 60
    if m >= 60:
        h += 1
        m -= 60

    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _is_dialogue_line(line: str) -> bool:
    return line.startswith("Dialogue:")


def _split_dialogue(line: str) -> list[str] | None:
    parts = line.split(",", 9)
    if len(parts) < 10:
        return None
    return parts


def _has_active_highlight(line: str) -> bool:
    return bool(_ACTIVE_HIGHLIGHT_TAG_RE.search(line))


def apply_caption_highlight_timing_nudge_to_ass_text(
    ass_text: str,
    *,
    nudge_seconds: float | None = None,
) -> str:
    if nudge_seconds is None:
        nudge_seconds = resolve_caption_highlight_timing_nudge_seconds()

    nudge = float(nudge_seconds)
    if abs(nudge) < 0.0001:
        return ass_text

    lines = ass_text.splitlines()

    # Gruppe = gleiche ASS-Start/End-Zeit.
    # Wenn eine Zeile in dieser Gruppe aktiv ist, wird der ganze visuelle Frame verschoben.
    active_time_groups: set[tuple[str, str]] = set()

    for line in lines:
        if not _is_dialogue_line(line):
            continue

        parts = _split_dialogue(line)
        if not parts:
            continue

        if _has_active_highlight(line):
            active_time_groups.add((parts[1], parts[2]))

    output: list[str] = []

    for line in lines:
        if not _is_dialogue_line(line):
            output.append(line)
            continue

        parts = _split_dialogue(line)
        if not parts:
            output.append(line)
            continue

        key = (parts[1], parts[2])
        if key not in active_time_groups:
            output.append(line)
            continue

        old_start = _ass_time_to_seconds(parts[1])
        old_end = _ass_time_to_seconds(parts[2])

        new_start = max(0.0, old_start + nudge)
        new_end = max(new_start + 0.01, old_end + nudge)

        parts[1] = _seconds_to_ass_time(new_start)
        parts[2] = _seconds_to_ass_time(new_end)

        output.append(",".join(parts))

    trailing_newline = "\n" if ass_text.endswith("\n") else ""
    return "\n".join(output) + trailing_newline
