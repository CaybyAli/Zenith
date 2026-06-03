from __future__ import annotations

import itertools
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ASS_FONT_ENV_VAR = "ZENITH_CAPTION_FONT_NAME"
DEFAULT_ASS_FONT_NAME = "Bangers"
ASS_HIGHLIGHT_GREEN = "&H0000FF00&"
ASS_HIGHLIGHT_YELLOW = "&H0000FFFF&"
ASS_DEFAULT_WHITE = "&H00FFFFFF"
ASS_OUTLINE_BLACK = "&H00000000"
DEFAULT_FONTS_DIR = Path(r"D:\Zenith\assets\fonts")

ASS_TEXT_DELAY_SECONDS = 0.12
ASS_GROUP_BREAK_GAP = 0.48
ASS_BLANK_ONLY_AFTER_SILENCE = 0.28
ASS_GROUP_TAIL_SECONDS = 0.16
ASS_MAX_WORD_DISPLAY_SECONDS = 0.72

ASS_NORMAL_MAX_WORDS = 3
ASS_FAST_MAX_WORDS = 5
ASS_FAST_GAP_MAX = 0.16
ASS_FAST_4_MAX_DURATION = 1.20
ASS_FAST_5_MAX_DURATION = 1.45
ASS_FAST_MAX_CHARS = 30

ASS_NORMAL_BASE_SIZE = 165
ASS_NORMAL_ACTIVE_SIZE = 225
ASS_SHORT_BASE_SIZE = 180
ASS_SHORT_ACTIVE_SIZE = 245
ASS_OUTLINE_SIZE = 18
ASS_WORD_GAP = r"\h\h"

ASS_ONE_LINE_Y = 1385
ASS_TWO_LINE_Y = (1310, 1445)

ASS_TARGET_WIDTH = 18.0
ASS_HARD_WIDTH = 22.0


@dataclass(frozen=True)
class CaptionGroup:
    words: list[Any]


@dataclass(frozen=True)
class CaptionASSWord:
    text: str
    start_seconds: float
    end_seconds: float
    speaker: str = "unknown"
    audio_track: str = "mic"


def escape_ffmpeg_filter_path(path: str | Path) -> str:
    """Escape a filesystem path for FFmpeg filter option strings."""
    if isinstance(path, Path):
        text = path.as_posix()
    else:
        text = str(path).replace("\\", "/")
    return re.sub(r"^([A-Za-z]):", r"\1\\\\:", text)


class CaptionASSBuilder:
    def generate_ass_file(
        self,
        caption_groups: list[CaptionGroup],
        output_path: str,
    ) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        groups = self.build_groups(caption_groups)

        lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "WrapStyle: 1",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,Bold,Italic,Underline,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV",
            (
                f"Style: Default,{self._font_name()},{ASS_NORMAL_BASE_SIZE},"
                f"{ASS_DEFAULT_WHITE},{ASS_OUTLINE_BLACK},0,0,0,1,"
                f"{ASS_OUTLINE_SIZE},0,5,10,10,0"
            ),
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]

        for event in self._dialogue_events_from_groups(groups):
            lines.append(event)

        path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
        return str(path)

    def build_groups(self, caption_groups: list[CaptionGroup]) -> list[list[CaptionASSWord]]:
        words = self._flatten_words(caption_groups)
        if not words:
            return []

        words = self._smooth_words(words)
        groups = self._make_groups_v27(words)
        groups = self._split_5_word_groups(groups)
        return groups

    def _flatten_words(self, caption_groups: list[CaptionGroup]) -> list[CaptionASSWord]:
        words: list[CaptionASSWord] = []

        for group in caption_groups:
            for raw_word in list(getattr(group, "words", []) or []):
                word = self._caption_word_from_any(raw_word)
                if word.text and word.end_seconds > word.start_seconds:
                    words.append(word)

        return sorted(
            words,
            key=lambda word: (
                word.start_seconds,
                self._speaker_priority(word),
                word.end_seconds,
            ),
        )

    def _smooth_words(self, words: list[CaptionASSWord]) -> list[CaptionASSWord]:
        smoothed: list[CaptionASSWord] = []
        previous_end = 0.0

        for word in words:
            start = max(0.0, float(word.start_seconds))
            raw_end = max(start + 0.08, float(word.end_seconds))
            end = min(raw_end, start + ASS_MAX_WORD_DISPLAY_SECONDS)

            if start < previous_end - 0.04:
                start = max(0.0, previous_end - 0.02)

            end = max(start + 0.08, end)

            smoothed.append(
                CaptionASSWord(
                    text=word.text,
                    start_seconds=start,
                    end_seconds=end,
                    speaker=word.speaker,
                    audio_track=word.audio_track,
                )
            )
            previous_end = end

        return smoothed

    def _make_groups_v27(self, words: list[CaptionASSWord]) -> list[list[CaptionASSWord]]:
        groups: list[list[CaptionASSWord]] = []
        current: list[CaptionASSWord] = []

        for word in words:
            should_break = False

            if current:
                gap = word.start_seconds - current[-1].end_seconds

                if self._is_sentence_end(current[-1].text):
                    should_break = True

                if gap >= ASS_GROUP_BREAK_GAP:
                    should_break = True

                if not self._same_caption_voice(current[-1], word):
                    should_break = True

                if not self._can_extend_fast(current, word):
                    should_break = True

            if should_break:
                groups.append(current)
                current = []

            current.append(word)

        if current:
            groups.append(current)

        return groups

    def _can_extend_fast(
        self,
        current: list[CaptionASSWord],
        word: CaptionASSWord,
    ) -> bool:
        if not current:
            return True

        candidate = [*current, word]
        count = len(candidate)

        if count <= ASS_NORMAL_MAX_WORDS:
            return True

        if count > ASS_FAST_MAX_WORDS:
            return False

        gap = word.start_seconds - current[-1].end_seconds
        duration = candidate[-1].end_seconds - candidate[0].start_seconds
        chars = len(" ".join(item.text for item in candidate))

        if gap > ASS_FAST_GAP_MAX:
            return False

        if chars > ASS_FAST_MAX_CHARS:
            return False

        if count == 4 and duration <= ASS_FAST_4_MAX_DURATION:
            return True

        if count == 5 and duration <= ASS_FAST_5_MAX_DURATION:
            return True

        return False

    def _split_5_word_groups(
        self,
        groups: list[list[CaptionASSWord]],
    ) -> list[list[CaptionASSWord]]:
        repaired: list[list[CaptionASSWord]] = []

        for group in groups:
            if len(group) != 5:
                repaired.append(group)
                continue

            first_2 = group[:2]
            last_3 = group[2:]
            first_3 = group[:3]
            last_2 = group[3:]

            width_23 = abs(
                sum(self._visual_width(word.text) for word in first_2)
                - sum(self._visual_width(word.text) for word in last_3)
            )
            width_32 = abs(
                sum(self._visual_width(word.text) for word in first_3)
                - sum(self._visual_width(word.text) for word in last_2)
            )

            if width_32 <= width_23:
                repaired.append(first_3)
                repaired.append(last_2)
            else:
                repaired.append(first_2)
                repaired.append(last_3)

        return repaired

    def _dialogue_events_from_groups(
        self,
        groups: list[list[CaptionASSWord]],
    ) -> list[str]:
        events: list[str] = []

        for group_index, group in enumerate(groups):
            if not group:
                continue

            lines = self._split_lines_balanced(group)
            next_group_start = (
                groups[group_index + 1][0].start_seconds
                if group_index + 1 < len(groups)
                else group[-1].end_seconds + ASS_GROUP_TAIL_SECONDS
            )

            gap_to_next_group = next_group_start - group[-1].end_seconds

            if gap_to_next_group <= ASS_BLANK_ONLY_AFTER_SILENCE:
                group_end = min(next_group_start, group[-1].end_seconds + ASS_GROUP_TAIL_SECONDS)
            else:
                group_end = group[-1].end_seconds + ASS_GROUP_TAIL_SECONDS

            if group_end <= group[0].start_seconds:
                group_end = group[-1].end_seconds + ASS_GROUP_TAIL_SECONDS

            base_size, active_size = self._group_font_sizes(group)
            group_end_cs = self._to_centiseconds(group_end)

            for active_index, active_word in enumerate(group):
                active_start_cs = self._to_centiseconds(active_word.start_seconds)

                if active_index + 1 < len(group):
                    active_end_cs = self._to_centiseconds(group[active_index + 1].start_seconds)
                else:
                    active_end_cs = group_end_cs

                if active_end_cs <= active_start_cs:
                    active_end_cs = active_start_cs + 8

                for line, y in zip(lines, self._y_positions_for(lines)):
                    parts: list[str] = []

                    for word in line:
                        word_text = self._escape_ass_text(word.text.upper())

                        if word is active_word:
                            active_colour = self._highlight_colour_for_word(word)
                            parts.append(
                                rf"{{\fs{active_size}\c{active_colour}}}"
                                + word_text
                                + rf"{{\fs{base_size}\c{ASS_DEFAULT_WHITE}}}"
                            )
                        else:
                            parts.append(word_text)

                    events.append(
                        f"Dialogue: 0,{self._format_ass_time_from_cs(active_start_cs)},"
                        f"{self._format_ass_time_from_cs(active_end_cs)},"
                        "Default,,0,0,0,,"
                        + rf"{{\an5\pos(540,{y})}}{{\fs{base_size}\c{ASS_DEFAULT_WHITE}}}"
                        + ASS_WORD_GAP.join(parts)
                    )

        return events

    def _split_lines_balanced(
        self,
        group: list[CaptionASSWord],
    ) -> list[list[CaptionASSWord]]:
        return min(
            self._all_layout_candidates(group),
            key=lambda lines: self._layout_score(group, lines),
        )

    def _all_layout_candidates(
        self,
        group: list[CaptionASSWord],
    ) -> list[list[list[CaptionASSWord]]]:
        count = len(group)

        if count <= 1:
            return [[group]]

        candidates: list[list[list[CaptionASSWord]]] = []
        max_lines = 1 if count <= 2 else 2

        for line_count in range(1, max_lines + 1):
            for splits in itertools.combinations(range(1, count), line_count - 1):
                points = [0, *splits, count]
                candidates.append(
                    [group[start:end] for start, end in zip(points, points[1:])]
                )

        return candidates

    def _layout_score(
        self,
        group: list[CaptionASSWord],
        lines: list[list[CaptionASSWord]],
    ) -> float:
        widths = [self._line_width(line) for line in lines]
        score = 0.0

        if len(lines) == 1:
            score += 0.0 if len(group) <= 2 else 10.0
        else:
            score += 3.0

        for width in widths:
            if width > ASS_TARGET_WIDTH:
                score += ((width - ASS_TARGET_WIDTH) ** 2) * 8.0
            if width > ASS_HARD_WIDTH:
                score += ((width - ASS_HARD_WIDTH) ** 2) * 35.0

        if len(widths) >= 2:
            score += (max(widths) - min(widths)) * 1.25

        for line in lines:
            if len(line) == 1:
                width = self._visual_width(line[0].text)
                if width <= 3.0:
                    score += 18.0
                elif width <= 5.0:
                    score += 9.0
                else:
                    score += 2.0

        line_lengths = [len(line) for line in lines]

        if len(group) == 4 and line_lengths == [2, 2]:
            score -= 5.0

        return score

    def _line_width(self, line: list[CaptionASSWord]) -> float:
        if not line:
            return 0.0

        active_scale = ASS_NORMAL_ACTIVE_SIZE / ASS_NORMAL_BASE_SIZE
        base = sum(self._visual_width(word.text) for word in line)
        gap_width = max(0, len(line) - 1) * 1.4
        max_word = max(self._visual_width(word.text) for word in line)
        active_extra = max_word * (active_scale - 1.0)

        return base + gap_width + active_extra

    @staticmethod
    def _visual_width(text: str) -> float:
        width = 0.0

        for char in str(text or "").upper():
            if char in "MW???":
                width += 1.35
            elif char in "I????J.,:;!'":
                width += 0.55
            elif char == "-":
                width += 0.75
            elif char == " ":
                width += 0.65
            else:
                width += 1.0

        return width

    @staticmethod
    def _y_positions_for(lines: list[list[CaptionASSWord]]) -> tuple[int, ...]:
        if len(lines) == 1:
            return (ASS_ONE_LINE_Y,)
        return ASS_TWO_LINE_Y

    @staticmethod
    def _group_font_sizes(group: list[CaptionASSWord]) -> tuple[int, int]:
        if len(group) <= 2:
            return ASS_SHORT_BASE_SIZE, ASS_SHORT_ACTIVE_SIZE
        return ASS_NORMAL_BASE_SIZE, ASS_NORMAL_ACTIVE_SIZE

    @staticmethod
    def _is_sentence_end(text: str) -> bool:
        clean = str(text or "").strip()
        return clean.endswith("?") or clean.endswith("!") or clean.endswith(".")

    @staticmethod
    def _font_name() -> str:
        return os.getenv(ASS_FONT_ENV_VAR, DEFAULT_ASS_FONT_NAME) or DEFAULT_ASS_FONT_NAME

    @staticmethod
    def _to_centiseconds(seconds: float) -> int:
        delayed = max(0.0, float(seconds) + ASS_TEXT_DELAY_SECONDS)
        return max(0, int(round(delayed * 100)))

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        total_centiseconds = max(0, int(round(float(seconds) * 100)))
        return CaptionASSBuilder._format_ass_time_from_cs(total_centiseconds)

    @staticmethod
    def _format_ass_time_from_cs(total_centiseconds: int) -> str:
        total_centiseconds = max(0, int(total_centiseconds))
        hours = total_centiseconds // 360000
        remainder = total_centiseconds % 360000
        minutes = remainder // 6000
        remainder %= 6000
        seconds = remainder // 100
        centiseconds = remainder % 100
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    @staticmethod
    def _same_caption_voice(left: CaptionASSWord, right: CaptionASSWord) -> bool:
        return CaptionASSBuilder._speaker_priority(left) == CaptionASSBuilder._speaker_priority(right)

    @staticmethod
    def _speaker_priority(word: CaptionASSWord) -> int:
        marker = f"{word.speaker} {word.audio_track}".casefold()
        if any(item in marker for item in ("mic", "owner", "ali", "hajar", "primary", "main")):
            return 0
        return 1

    @staticmethod
    def _highlight_colour_for_word(word: CaptionASSWord) -> str:
        marker = f"{word.speaker} {word.audio_track}".casefold()
        if any(item in marker for item in ("discord", "friend", "secondary", "teammate", "team")):
            return ASS_HIGHLIGHT_YELLOW
        return ASS_HIGHLIGHT_GREEN

    @staticmethod
    def _caption_word_from_any(word: Any) -> CaptionASSWord:
        if isinstance(word, dict):
            text = word.get("word") or word.get("text") or ""
            start = word.get("start_seconds", word.get("start", 0.0))
            end = word.get("end_seconds", word.get("end", start))
            speaker = word.get("speaker", "unknown")
            audio_track = word.get("audio_track", "mic")
        else:
            text = getattr(word, "text", None) or getattr(word, "word", "")
            start = getattr(word, "start_seconds", getattr(word, "start", 0.0))
            end = getattr(word, "end_seconds", getattr(word, "end", start))
            speaker = getattr(word, "speaker", "unknown")
            audio_track = getattr(word, "audio_track", "mic")

        return CaptionASSWord(
            text=" ".join(str(text or "").split()),
            start_seconds=float(start or 0.0),
            end_seconds=float(end or 0.0),
            speaker=str(speaker or "unknown"),
            audio_track=str(audio_track or "mic"),
        )

    @staticmethod
    def _word_text(word: Any) -> str:
        return CaptionASSBuilder._caption_word_from_any(word).text

    @staticmethod
    def _word_start(word: Any) -> float:
        return CaptionASSBuilder._caption_word_from_any(word).start_seconds

    @staticmethod
    def _word_end(word: Any) -> float:
        return CaptionASSBuilder._caption_word_from_any(word).end_seconds

    @staticmethod
    def _escape_ass_text(value: str) -> str:
        text = str(value or "")
        text = text.replace("{", "(").replace("}", ")")
        text = text.replace("\n", " ").replace("\r", " ")
        return " ".join(text.split())


def _caption_word_from_segment(segment: Any) -> CaptionASSWord:
    return CaptionASSBuilder._caption_word_from_any(segment)


def build_ass_file(
    segments: list[Any],
    highlight_words: list[str] | None = None,
    output_path: str = "captions.ass",
) -> str:
    """Compatibility helper for D7 probe-clip mode."""
    words = [_caption_word_from_segment(segment) for segment in segments]
    words = [word for word in words if word.text and word.end_seconds > word.start_seconds]
    return CaptionASSBuilder().generate_ass_file(
        caption_groups=[CaptionGroup(words=words)] if words else [],
        output_path=output_path,
    )
