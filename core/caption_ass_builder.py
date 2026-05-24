from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ASS_FONT_ENV_VAR = "ZENITH_CAPTION_FONT_NAME"
DEFAULT_ASS_FONT_NAME = "Bangers"
ASS_HIGHLIGHT_GREEN = "&H0000FF00&"
ASS_DEFAULT_WHITE = "&H00FFFFFF"
ASS_OUTLINE_BLACK = "&H00000000"
DEFAULT_FONTS_DIR = Path(r"D:\Zenith\assets\fonts")


@dataclass(frozen=True)
class CaptionGroup:
    words: list[Any]


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

        lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "WrapStyle: 1",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,Bold,Italic,Underline,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV",
            f"Style: Default,{self._font_name()},72,{ASS_DEFAULT_WHITE},{ASS_OUTLINE_BLACK},0,0,0,1,8,0,2,10,10,100",
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]

        for group in caption_groups:
            lines.extend(self._dialogue_events(group))

        path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
        return str(path)

    def _dialogue_events(self, group: CaptionGroup) -> list[str]:
        words = list(getattr(group, "words", []) or [])
        if not words:
            return []

        clean_words = [self._word_text(word).upper() for word in words]
        events: list[str] = []

        for index, word in enumerate(words):
            start = self._word_start(word)
            end = self._word_end(word)
            if end <= start:
                continue

            highlighted = self._highlight_text(clean_words, index)
            events.append(
                "Dialogue: "
                f"0,{self._format_ass_time(start)},{self._format_ass_time(end)},"
                f"Default,,0,0,0,,{highlighted}"
            )

        return events

    def _highlight_text(self, words: list[str], active_index: int) -> str:
        parts: list[str] = []
        for index, word in enumerate(words):
            safe_word = self._escape_ass_text(word)
            if index == active_index:
                parts.append(f"{{\\c{ASS_HIGHLIGHT_GREEN}}}{safe_word}{{\\r}}")
            else:
                parts.append(safe_word)
        return " ".join(parts)

    @staticmethod
    def _font_name() -> str:
        return os.getenv(ASS_FONT_ENV_VAR, DEFAULT_ASS_FONT_NAME) or DEFAULT_ASS_FONT_NAME

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        total_centiseconds = max(0, int(round(float(seconds) * 100)))
        hours = total_centiseconds // 360000
        remainder = total_centiseconds % 360000
        minutes = remainder // 6000
        remainder %= 6000
        secs = remainder // 100
        centiseconds = remainder % 100
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

    @staticmethod
    def _word_text(word: Any) -> str:
        value = getattr(word, "text", None)
        if value is None:
            value = getattr(word, "word", "")
        return " ".join(str(value or "").split())

    @staticmethod
    def _word_start(word: Any) -> float:
        for attr in ("start_seconds", "start", "start_time"):
            value = getattr(word, attr, None)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    @staticmethod
    def _word_end(word: Any) -> float:
        for attr in ("end_seconds", "end", "end_time"):
            value = getattr(word, attr, None)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    @staticmethod
    def _escape_ass_text(value: str) -> str:
        text = str(value or "")
        text = text.replace("{", "(").replace("}", ")")
        text = text.replace("\n", " ").replace("\r", " ")
        return " ".join(text.split())


@dataclass(frozen=True)
class CaptionASSWord:
    text: str
    start_seconds: float
    end_seconds: float


def _caption_word_from_segment(segment: Any) -> CaptionASSWord:
    if isinstance(segment, dict):
        text = segment.get("word") or segment.get("text") or ""
        start = segment.get("start_seconds", segment.get("start", 0.0))
        end = segment.get("end_seconds", segment.get("end", start))
    else:
        text = getattr(segment, "text", None) or getattr(segment, "word", "")
        start = getattr(segment, "start_seconds", getattr(segment, "start", 0.0))
        end = getattr(segment, "end_seconds", getattr(segment, "end", start))

    return CaptionASSWord(
        text=" ".join(str(text or "").split()),
        start_seconds=float(start or 0.0),
        end_seconds=float(end or 0.0),
    )


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

