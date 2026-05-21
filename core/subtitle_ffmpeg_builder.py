from __future__ import annotations

from typing import Any

from core.subtitle_generator import SubtitleSegment, SubtitleStyle


class SubtitleFFmpegBuilder:
    @staticmethod
    def build_filter_string(segments: list[SubtitleSegment]) -> str:
        """
        Baut deterministischen FFmpeg drawtext-Filterstring aus Segmentliste.
        Gibt leeren String "" zurück wenn segments leer.

        Jedes Segment erzeugt:
        1. Base drawtext: kompletter text, font_color, font_size, box
        2. Pro Highlight-Wort: zweiten drawtext-Layer mit highlight_color, highlight_size

        enable='between(t,{start:.3f},{end:.3f})' immer gesetzt.
        Einzelne Filter durch Komma getrennt (FFmpeg filtergraph-Format).

        DETERMINISTISCH: gleicher Input → immer identischer String.
        Keine uuid, keine timestamps, keine Zufallswerte.
        """
        try:
            if not isinstance(segments, list) or not segments:
                return ""

            filters: list[str] = []

            for segment in segments:
                style = getattr(segment, "style", SubtitleStyle())
                if not isinstance(style, SubtitleStyle):
                    style = SubtitleStyle()

                text = SubtitleFFmpegBuilder._safe_str(
                    getattr(segment, "text", "")
                )
                start = SubtitleFFmpegBuilder._safe_float(
                    getattr(segment, "start", 0.0)
                )
                end = SubtitleFFmpegBuilder._safe_float(
                    getattr(segment, "end", 0.0)
                )

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
                        end=end,
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
                            start=start,
                            end=end,
                        )
                    )

            return ",".join(filters)
        except Exception:
            return ""

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
