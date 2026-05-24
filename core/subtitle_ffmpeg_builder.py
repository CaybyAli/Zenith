from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from core.subtitle_generator import SubtitleSegment, SubtitleStyle


LONGFORM_STANDARD_STYLE = "longform_standard"
MOBILE_FIRST_STYLE = "mobile_first"
MOBILE_FIRST_FONT_SIZE = 86
MOBILE_FIRST_HIGHLIGHT_SIZE = 86
MOBILE_FIRST_Y = "h*0.58"
MOBILE_FIRST_X = "(w-text_w)/2"
MOBILE_FIRST_BOX_COLOR = "black@0.0"
MOBILE_FIRST_WORDS_PER_LINE = 3
MOBILE_FIRST_BORDER_WIDTH = 10
MOBILE_FIRST_BORDER_COLOR = "black"
MOBILE_FIRST_HIGHLIGHT_COLOR = "#00FF38"
MOBILE_FIRST_SHADOW_COLOR = "black@0.0"
MOBILE_FIRST_SHADOW_X = 0
MOBILE_FIRST_SHADOW_Y = 0
MOBILE_FIRST_LINE_SPACING = 12
MOBILE_FIRST_CHAR_WIDTH_FACTOR = 0.55
MOBILE_FIRST_WORD_GAP_PX = 20
MOBILE_FIRST_MIN_STATE_SECONDS = 0.18
FALLBACK_FONT_FAMILY = "Impact"
DEFAULT_SUBTITLE_FONT_FILE = r"D:\Zenith\assets\fonts\Bangers-Regular.ttf"
SUBTITLE_FONT_ENV_VAR = "ZENITH_SUBTITLE_FONT_FILE"
BANGERS_FONT_URL = (
    "https://fonts.gstatic.com/s/bangers/v24/FeVQS0BTqb0h60ACL5la2bxii28wYQ.ttf"
)


def _resolve_font() -> str:
    env_font = os.environ.get(SUBTITLE_FONT_ENV_VAR)
    if env_font and _is_usable_font(env_font):
        return env_font

    local_font = Path(DEFAULT_SUBTITLE_FONT_FILE)
    if _is_usable_font(local_font):
        return str(local_font)

    try:
        local_font.parent.mkdir(parents=True, exist_ok=True)
        import urllib.request

        urllib.request.urlretrieve(BANGERS_FONT_URL, local_font)
        if _is_usable_font(local_font):
            return str(local_font)
    except Exception:
        pass

    import warnings

    warnings.warn(
        "Bangers missing, using fallback font Impact. "
        r"For final style, install D:\Zenith\assets\fonts\Bangers-Regular.ttf.",
        RuntimeWarning,
    )
    return FALLBACK_FONT_FAMILY


def _is_usable_font(path: str | Path) -> bool:
    try:
        candidate = Path(path)
        return candidate.exists() and candidate.stat().st_size > 10_000
    except Exception:
        return False


FONT_FILE = _resolve_font()


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
                duration = end - start
                if duration <= 0.0:
                    mid = end
                else:
                    mid = start + (duration / 2.0)
                if duration > 0.002:
                    mid = max(start + 0.001, min(mid, end - 0.001))

                if mid > start:
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
                    if end <= mid:
                        continue
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

        full_text = " ".join(str(word["text"]) for word in words)
        char_width = MOBILE_FIRST_FONT_SIZE * MOBILE_FIRST_CHAR_WIDTH_FACTOR
        word_offsets: list[float] = []
        next_offset = 0.0
        word_advance_gap = MOBILE_FIRST_WORD_GAP_PX + (MOBILE_FIRST_BORDER_WIDTH * 2)
        for word in words:
            word_offsets.append(next_offset)
            next_offset += (
                len(str(word["text"])) * char_width
                + word_advance_gap
            )

        full_width = max(0.0, next_offset - word_advance_gap)
        base_x = f"(w/2)-{full_width / 2.0:.3f}"

        filters: list[str] = [
            SubtitleFFmpegBuilder._mobile_drawtext_timed(
                text=full_text,
                font_color="white",
                font_size=MOBILE_FIRST_FONT_SIZE,
                x=MOBILE_FIRST_X,
                alpha_start=-1.0,
                alpha_end=-1.0,
            )
        ]

        group_end = float(words[-1]["end"])
        for index, word in enumerate(words):
            enable_start = float(word["start"])
            has_next_word = index + 1 < len(words)
            if has_next_word:
                enable_end = float(words[index + 1]["start"])
            else:
                enable_end = max(
                    group_end,
                    enable_start + MOBILE_FIRST_MIN_STATE_SECONDS,
                )

            if enable_end <= enable_start:
                enable_end = max(
                    float(word["end"]),
                    enable_start + MOBILE_FIRST_MIN_STATE_SECONDS,
                )

            for display_index, display_word in enumerate(words):
                font_color = (
                    MOBILE_FIRST_HIGHLIGHT_COLOR
                    if display_index == index
                    else "white"
                )
                font_size = (
                    MOBILE_FIRST_HIGHLIGHT_SIZE
                    if display_index == index
                    else MOBILE_FIRST_FONT_SIZE
                )

                filters.append(
                    SubtitleFFmpegBuilder._mobile_drawtext_timed(
                        text=str(display_word["text"]),
                        font_color=font_color,
                        font_size=font_size,
                        x=f"{base_x}+{word_offsets[display_index]:.1f}",
                        enable_start=enable_start,
                        enable_end=enable_end,
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
        try:
            if FONT_FILE and Path(FONT_FILE).exists():
                return f"fontfile='{SubtitleFFmpegBuilder._escape_filter_value(FONT_FILE)}'"
        except Exception:
            pass
        return f"font={SubtitleFFmpegBuilder._safe_str(FONT_FILE, FALLBACK_FONT_FAMILY)}"

    @staticmethod
    def _escape_filter_value(value) -> str:
        """Escape a filesystem path for use as an FFmpeg drawtext option value.

        FFmpeg's drawtext filter uses ':' as an option separator and '\\' as an
        escape character. On Windows the drive letter produces a literal ':'
        (e.g. ``D:``), which FFmpeg would misparse as an option boundary.

        Strategy:
          1. Normalise all path separators to forward-slashes so backslashes
             are not misread as FFmpeg escape sequences.
          2. Escape the drive-letter colon (``D:`` -> ``D\\:``) so FFmpeg treats
             it as a literal colon inside the option value.
          3. Escape any remaining bare single-quotes that could break the
             surrounding ``drawtext=text='...'`` quoting.
        """
        text = SubtitleFFmpegBuilder._safe_str(value)
        text = text.replace("\\", "/")
        if len(text) >= 2 and text[1] == ":":
            text = text[0] + "\\:" + text[2:]
        text = text.replace("'", "\\'")
        return text

    @staticmethod
    def _escape_mobile_text(value) -> str:
        newline_token = "__ZENITH_MOBILE_NEWLINE__"
        text = SubtitleFFmpegBuilder._safe_str(value).replace("\\n", newline_token)
        text = SubtitleFFmpegBuilder._escape_drawtext_text(text)
        text = text.replace(newline_token, "\\n")
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
    def _escape_drawtext_text(raw: str) -> str:
        """Escape special chars that break FFmpeg drawtext filter syntax."""
        escaped = SubtitleFFmpegBuilder._safe_str(raw)
        escaped = escaped.replace("\\", "\\\\")
        escaped = escaped.replace("'", "\\'")
        escaped = escaped.replace(":", "\\:")
        escaped = escaped.replace("[", "\\[")
        escaped = escaped.replace("]", "\\]")
        return escaped

    @staticmethod
    def _escape_text(value: Any) -> str:
        text = SubtitleFFmpegBuilder._safe_str(value)
        text = " ".join(text.splitlines())
        text = SubtitleFFmpegBuilder._escape_drawtext_text(text)
        text = text.replace(",", "\\,")
        text = text.replace("%", "\\%")
        return text
