from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from core.subtitle_generator import SubtitleSegment, SubtitleStyle


LONGFORM_STANDARD_STYLE = "longform_standard"
MOBILE_FIRST_STYLE = "mobile_first"
MOBILE_FIRST_FONT_SIZE = 72
MOBILE_FIRST_HIGHLIGHT_SIZE = 72
MOBILE_FIRST_Y = "h*0.72"
MOBILE_FIRST_X = "(w-text_w)/2"
MOBILE_FIRST_BOX_COLOR = "black@0.0"
MOBILE_FIRST_WORDS_PER_LINE = 3
MOBILE_FIRST_BORDER_WIDTH = 8
MOBILE_FIRST_BORDER_COLOR = "black"
MOBILE_FIRST_HIGHLIGHT_COLOR = "#00FF00"
MOBILE_FIRST_SHADOW_COLOR = "black@0.75"
MOBILE_FIRST_SHADOW_X = 2
MOBILE_FIRST_SHADOW_Y = 2
MOBILE_FIRST_LINE_SPACING = 12
MOBILE_FIRST_CHAR_WIDTH_FACTOR = 0.55
FALLBACK_FONT_FAMILY = "Arial"
DEFAULT_SUBTITLE_FONT_FILE = r"D:\Zenith\assets\fonts\Bangers-Regular.ttf"
SUBTITLE_FONT_ENV_VAR = "ZENITH_SUBTITLE_FONT_FILE"


class SubtitleFFmpegBuilder:
    @staticmethod
    def build_filter(
        words: list[str],
        style: Literal["mobile_first", "longform_standard"] = LONGFORM_STANDARD_STYLE,
        highlighted_words: list[str] | None = None,
    ) -> str:
        safe_words = SubtitleFFmpegBuilder._safe_words(words)
        safe_highlights = SubtitleFFmpegBuilder._safe_words(highlighted_words or [])

        if style == MOBILE_FIRST_STYLE:
            return SubtitleFFmpegBuilder._build_mobile_first_filter(
                words=safe_words,
                highlighted_words=safe_highlights,
            )

        if not safe_words:
            return ""

        segment = SubtitleSegment(
            text=" ".join(safe_words),
            start=0.0,
            end=999.0,
            highlight_words=safe_highlights,
            style=SubtitleStyle(),
        )
        return SubtitleFFmpegBuilder.build_filter_string([segment])

    @staticmethod
    def build_filter_string(segments: list[SubtitleSegment]) -> str:
        try:
            if not isinstance(segments, list):
                segments = [segments]
            if not segments:
                return ""

            filters: list[str] = []

            for segment in segments:
                karaoke_filters = SubtitleFFmpegBuilder._karaoke_word_pop_filters(segment)
                if karaoke_filters:
                    filters.extend(karaoke_filters)
                    continue

                style = getattr(segment, "style", SubtitleStyle())
                if not isinstance(style, SubtitleStyle):
                    style = SubtitleStyle()

                text = SubtitleFFmpegBuilder._safe_str(getattr(segment, "text", ""))
                start = SubtitleFFmpegBuilder._safe_float(getattr(segment, "start", 0.0))
                end = SubtitleFFmpegBuilder._safe_float(getattr(segment, "end", 0.0))
                mid = start + ((end - start) / 2.0)

                filters.append(
                    SubtitleFFmpegBuilder._drawtext(
                        text=text,
                        font_color=style.font_color,
                        font_size=style.font_size,
                        box=style.box,
                        box_color=style.box_color,
                        x=style.x,
                        y=style.y,
                        start=start,
                        end=mid,
                    )
                )

                for word in SubtitleFFmpegBuilder._safe_words(
                    getattr(segment, "highlight_words", [])
                ):
                    filters.append(
                        SubtitleFFmpegBuilder._drawtext(
                            text=word,
                            font_color=style.highlight_color,
                            font_size=style.highlight_size,
                            box=False,
                            box_color=style.box_color,
                            x=style.x,
                            y=style.y,
                            start=mid,
                            end=end,
                        )
                    )

            return ",".join(filters)
        except Exception:
            return ""

    @staticmethod
    def _karaoke_word_pop_filters(segment: Any) -> list[str]:
        words = SubtitleFFmpegBuilder._timed_words_from_segment(segment)
        if not words:
            return []

        full_text = " ".join(word["text"] for word in words)
        start = min(float(word["start"]) for word in words)
        end = max(float(word["end"]) for word in words)
        filters = [
            SubtitleFFmpegBuilder._mobile_drawtext_timed(
                text=full_text,
                font_color="white",
                font_size=MOBILE_FIRST_FONT_SIZE,
                x=MOBILE_FIRST_X,
                alpha_start=start,
                alpha_end=end,
            )
        ]

        char_width = MOBILE_FIRST_FONT_SIZE * MOBILE_FIRST_CHAR_WIDTH_FACTOR
        for index, word in enumerate(words):
            prefix_text = " ".join(item["text"] for item in words[:index])
            if prefix_text:
                prefix_text += " "
            x_offset = len(prefix_text) * char_width
            filters.append(
                SubtitleFFmpegBuilder._mobile_drawtext_timed(
                    text=word["text"],
                    font_color=MOBILE_FIRST_HIGHLIGHT_COLOR,
                    font_size=MOBILE_FIRST_HIGHLIGHT_SIZE,
                    x=f"{MOBILE_FIRST_X} + {x_offset:.3f}",
                    enable_start=float(word["start"]),
                    enable_end=float(word["end"]),
                )
            )

        return filters

    @staticmethod
    def _mobile_drawtext_timed(
        *,
        text: Any,
        font_color: Any,
        font_size: Any,
        x: Any,
        enable_start: float | None = None,
        enable_end: float | None = None,
        alpha_start: float | None = None,
        alpha_end: float | None = None,
    ) -> str:
        uppercase_text = SubtitleFFmpegBuilder._uppercase_preserving_mobile_newlines(text)
        parts = [
            f"drawtext=text='{SubtitleFFmpegBuilder._escape_mobile_text(uppercase_text)}'",
            SubtitleFFmpegBuilder._font_part(),
            f"fontcolor={SubtitleFFmpegBuilder._safe_str(font_color, 'white')}",
            f"fontsize={SubtitleFFmpegBuilder._safe_int(font_size, MOBILE_FIRST_FONT_SIZE)}",
            "box=0",
            f"borderw={MOBILE_FIRST_BORDER_WIDTH}",
            f"bordercolor={MOBILE_FIRST_BORDER_COLOR}",
            f"shadowcolor={MOBILE_FIRST_SHADOW_COLOR}",
            f"shadowx={MOBILE_FIRST_SHADOW_X}",
            f"shadowy={MOBILE_FIRST_SHADOW_Y}",
            f"line_spacing={MOBILE_FIRST_LINE_SPACING}",
            "fix_bounds=1",
            f"x={SubtitleFFmpegBuilder._safe_str(x, MOBILE_FIRST_X)}",
            f"y={MOBILE_FIRST_Y}",
        ]

        if alpha_start is not None and alpha_end is not None:
            parts.append(f"alpha='between(t,{alpha_start:.3f},{alpha_end:.3f})'")
        if enable_start is not None and enable_end is not None:
            parts.append(f"enable='between(t,{enable_start:.3f},{enable_end:.3f})'")

        return ":".join(parts)

    @staticmethod
    def _timed_words_from_segment(segment: Any) -> list[dict[str, float | str]]:
        raw_words = getattr(segment, "words", None)
        if not isinstance(raw_words, list) or not raw_words:
            return []

        result: list[dict[str, float | str]] = []
        for raw_word in raw_words:
            text = SubtitleFFmpegBuilder._safe_str(
                SubtitleFFmpegBuilder._first_word_value(raw_word, ("text", "word"))
            )
            text = " ".join(text.split()).upper()
            if not text:
                continue

            start = SubtitleFFmpegBuilder._safe_float(
                SubtitleFFmpegBuilder._first_word_value(
                    raw_word,
                    ("start", "start_seconds", "start_time"),
                )
            )
            end = SubtitleFFmpegBuilder._safe_float(
                SubtitleFFmpegBuilder._first_word_value(
                    raw_word,
                    ("end", "end_seconds", "end_time"),
                )
            )
            if end <= start:
                continue

            result.append({"text": text, "start": start, "end": end})

        return result

    @staticmethod
    def _first_word_value(source: Any, keys: tuple[str, ...]) -> Any:
        if isinstance(source, dict):
            for key in keys:
                if key in source and source.get(key) is not None:
                    return source.get(key)
            return None

        for key in keys:
            try:
                value = getattr(source, key)
            except Exception:
                continue
            if value is not None:
                return value

        return None

    @staticmethod
    def _drawtext(
        *,
        text: Any,
        font_color: Any,
        font_size: Any,
        box: Any,
        box_color: Any,
        x: Any,
        y: Any,
        start: float,
        end: float,
    ) -> str:
        parts = [
            f"drawtext=text='{SubtitleFFmpegBuilder._escape_text(text)}'",
            f"fontcolor={SubtitleFFmpegBuilder._safe_str(font_color, 'white')}",
            f"fontsize={SubtitleFFmpegBuilder._safe_int(font_size, 48)}",
            f"box={1 if bool(box) else 0}",
        ]

        if bool(box):
            parts.append(
                f"boxcolor={SubtitleFFmpegBuilder._safe_str(box_color, 'black@0.4')}"
            )

        parts.extend(
            [
                f"x={SubtitleFFmpegBuilder._safe_str(x, '(w-text_w)/2')}",
                f"y={SubtitleFFmpegBuilder._safe_str(y, 'h-100')}",
                f"enable='between(t,{start:.3f},{end:.3f})'",
            ]
        )

        return ":".join(parts)

    @staticmethod
    def _build_mobile_first_filter(
        *,
        words: list[str],
        highlighted_words: list[str],
    ) -> str:
        if not words:
            return ""

        text = SubtitleFFmpegBuilder._mobile_line_wrap(words)
        filters = [
            SubtitleFFmpegBuilder._mobile_drawtext(
                text=text,
                font_color="white",
                font_size=MOBILE_FIRST_FONT_SIZE,
                box=False,
                box_color=MOBILE_FIRST_BOX_COLOR,
            )
        ]

        for word in highlighted_words[:1]:
            filters.append(
                SubtitleFFmpegBuilder._mobile_drawtext(
                    text=word,
                    font_color=MOBILE_FIRST_HIGHLIGHT_COLOR,
                    font_size=MOBILE_FIRST_HIGHLIGHT_SIZE,
                    box=False,
                    box_color=MOBILE_FIRST_BOX_COLOR,
                )
            )

        return ",".join(filters)

    @staticmethod
    def _mobile_line_wrap(words: list[str]) -> str:
        chunks: list[str] = []
        for index in range(0, len(words), MOBILE_FIRST_WORDS_PER_LINE):
            chunks.append(" ".join(words[index:index + MOBILE_FIRST_WORDS_PER_LINE]))
        return "\\n".join(chunks)

    @staticmethod
    def _mobile_drawtext(
        *,
        text,
        font_color,
        font_size,
        box,
        box_color,
    ) -> str:
        uppercase_text = SubtitleFFmpegBuilder._uppercase_preserving_mobile_newlines(text)
        parts = [
            f"drawtext=text='{SubtitleFFmpegBuilder._escape_mobile_text(uppercase_text)}'",
            SubtitleFFmpegBuilder._font_part(),
            f"fontcolor={SubtitleFFmpegBuilder._safe_str(font_color, 'white')}",
            f"fontsize={SubtitleFFmpegBuilder._safe_int(font_size, MOBILE_FIRST_FONT_SIZE)}",
            f"box={1 if bool(box) else 0}",
            f"borderw={MOBILE_FIRST_BORDER_WIDTH}",
            f"bordercolor={MOBILE_FIRST_BORDER_COLOR}",
            f"shadowcolor={MOBILE_FIRST_SHADOW_COLOR}",
            f"shadowx={MOBILE_FIRST_SHADOW_X}",
            f"shadowy={MOBILE_FIRST_SHADOW_Y}",
            f"line_spacing={MOBILE_FIRST_LINE_SPACING}",
            "fix_bounds=1",
        ]

        if bool(box):
            parts.append(
                f"boxcolor={SubtitleFFmpegBuilder._safe_str(box_color, MOBILE_FIRST_BOX_COLOR)}"
            )

        parts.extend([f"x={MOBILE_FIRST_X}", f"y={MOBILE_FIRST_Y}"])
        return ":".join(parts)

    @staticmethod
    def _uppercase_preserving_mobile_newlines(value: Any) -> str:
        text = SubtitleFFmpegBuilder._safe_str(value)
        return "\\n".join(part.upper() for part in text.split("\\n"))

    @staticmethod
    def _font_part() -> str:
        font_path = os.environ.get(SUBTITLE_FONT_ENV_VAR, "")
        if not font_path and Path(DEFAULT_SUBTITLE_FONT_FILE).exists():
            font_path = DEFAULT_SUBTITLE_FONT_FILE
        try:
            if font_path and Path(font_path).exists():
                return f"fontfile={SubtitleFFmpegBuilder._escape_filter_value(font_path)}"
        except Exception:
            pass
        return f"font={FALLBACK_FONT_FAMILY}"

    @staticmethod
    def _escape_filter_value(value) -> str:
        text = SubtitleFFmpegBuilder._safe_str(value)
        text = text.replace("\\", "\\\\")
        text = text.replace(":", "\\:")
        text = text.replace("'", "\\'")
        return text

    @staticmethod
    def _escape_mobile_text(value) -> str:
        text = SubtitleFFmpegBuilder._safe_str(value)
        text = text.replace("'", "\\'")
        text = text.replace(":", "\\:")
        text = text.replace(",", "\\,")
        text = text.replace("%", "\\%")
        return text

    @staticmethod
    def _safe_words(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []

        result: list[str] = []
        seen: set[str] = set()

        for item in value:
            text = " ".join(SubtitleFFmpegBuilder._safe_str(item).split())
            if not text:
                continue

            key = text.casefold()
            if key in seen:
                continue

            result.append(text)
            seen.add(key)

        return result

    @staticmethod
    def _safe_str(value: Any, default: str = "") -> str:
        if value is None:
            return default
        try:
            text = str(value)
        except Exception:
            return default
        return text if text else default

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _escape_text(value: Any) -> str:
        text = SubtitleFFmpegBuilder._safe_str(value)
        text = " ".join(text.splitlines())
        text = text.replace("\\", "\\\\")
        text = text.replace("'", "\\'")
        text = text.replace(":", "\\:")
        text = text.replace(",", "\\,")
        text = text.replace("%", "\\%")
        return text
