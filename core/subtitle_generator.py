from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SubtitleStyle:
    font_size: int = 48
    font_color: str = "white"
    highlight_color: str = "yellow"
    highlight_size: int = 56
    box: bool = True
    box_color: str = "black@0.4"
    x: str = "(w-text_w)/2"
    y: str = "h-100"


@dataclass
class SubtitleSegment:
    text: str
    start: float
    end: float
    highlight_words: list[str]
    style: SubtitleStyle


class SubtitleGenerator:
    def __init__(
        self,
        transcript_segments: list[dict[str, Any]] | None = None,
        unified_edit_signals: list[dict[str, Any]] | None = None,
        style: SubtitleStyle | None = None,
    ) -> None:
        self.transcript_segments = self._safe_dict_list(transcript_segments)
        self.unified_edit_signals = self._safe_dict_list(unified_edit_signals)
        self.style = style if isinstance(style, SubtitleStyle) else SubtitleStyle()

    @classmethod
    def from_job(cls, job) -> "SubtitleGenerator":
        """Liest transcript_segments und keyword_emotion-Signale sicher aus."""
        try:
            transcript_segments = getattr(job, "transcript_segments", [])
        except Exception:
            transcript_segments = []

        try:
            unified_edit_signals = getattr(job, "unified_edit_signals", [])
        except Exception:
            unified_edit_signals = []

        return cls(
            transcript_segments=transcript_segments,
            unified_edit_signals=unified_edit_signals,
        )

    def generate(self) -> list[SubtitleSegment]:
        """
        Erzeugt SubtitleSegment-Liste aus transcript_segments.
        Highlight-Wörter kommen aus keyword_emotion-Signalen.
        Wenn kein Transcript vorhanden: leere Liste, kein Crash.
        Wenn kein Signal vorhanden: Segmente ohne Highlights.
        """
        try:
            if not isinstance(self.transcript_segments, list):
                return []

            segments: list[SubtitleSegment] = []

            for raw_segment in self.transcript_segments:
                if not isinstance(raw_segment, dict):
                    continue

                try:
                    text = self._safe_str(raw_segment.get("text", ""))
                    start = self._safe_float(
                        self._first_value(
                            raw_segment,
                            ("start", "start_seconds", "start_time"),
                        )
                    )
                    end = self._safe_float(
                        self._first_value(
                            raw_segment,
                            ("end", "end_seconds", "end_time"),
                        )
                    )

                    segments.append(
                        SubtitleSegment(
                            text=text,
                            start=start,
                            end=end,
                            highlight_words=self._highlight_words_for_segment(
                                text=text,
                                start=start,
                                end=end,
                            ),
                            style=self._clone_style(),
                        )
                    )
                except Exception:
                    continue

            return segments
        except Exception:
            return []

    @staticmethod
    def highlighted_word_selector(
        words: list[str],
        hook_scores: dict[str, float],
    ) -> list[str]:
        if not isinstance(words, list) or not isinstance(hook_scores, dict):
            return []

        highlighted: list[str] = []
        seen: set[str] = set()

        for word in words:
            clean = " ".join(SubtitleGenerator._safe_str(word).split())
            if not clean:
                continue

            try:
                score = float(hook_scores.get(clean, hook_scores.get(clean.casefold(), 0.0)) or 0.0)
            except Exception:
                score = 0.0

            if score <= 0.7:
                continue

            key = clean.casefold()
            if key in seen:
                continue

            highlighted.append(clean)
            seen.add(key)

        return highlighted

    @staticmethod
    def _safe_dict_list(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]

    @staticmethod
    def _safe_str(value: Any) -> str:
        if value is None:
            return ""
        try:
            return str(value)
        except Exception:
            return ""

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _safe_optional_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _first_value(source: dict[str, Any], keys: tuple[str, ...]) -> Any:
        for key in keys:
            if key in source and source.get(key) is not None:
                return source.get(key)
        return None

    def _clone_style(self) -> SubtitleStyle:
        return SubtitleStyle(
            font_size=int(self.style.font_size),
            font_color=str(self.style.font_color),
            highlight_color=str(self.style.highlight_color),
            highlight_size=int(self.style.highlight_size),
            box=bool(self.style.box),
            box_color=str(self.style.box_color),
            x=str(self.style.x),
            y=str(self.style.y),
        )

    def _keyword_emotion_signals(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        for signal in self.unified_edit_signals:
            if not isinstance(signal, dict):
                continue

            source = self._safe_str(signal.get("source")).strip().lower()
            signal_type = self._safe_str(signal.get("signal_type")).strip().lower()

            if source == "keyword_emotion" or "keyword" in signal_type:
                result.append(signal)

        return result

    def _highlight_words_for_segment(
        self,
        text: str,
        start: float,
        end: float,
    ) -> list[str]:
        words: list[str] = []
        text_folded = self._safe_str(text).casefold()

        for signal in self._keyword_emotion_signals():
            if not self._signal_overlaps_segment(signal, start, end):
                continue

            for field_name in ("word", "keywords", "highlight_words"):
                self._collect_words(words, signal.get(field_name))

        clean_words: list[str] = []
        seen: set[str] = set()

        for word in words:
            clean = " ".join(self._safe_str(word).split())
            if not clean:
                continue

            key = clean.casefold()
            if key in seen:
                continue

            if text_folded and key not in text_folded:
                continue

            clean_words.append(clean)
            seen.add(key)

        return clean_words

    def _collect_words(self, output: list[str], value: Any) -> None:
        try:
            if value is None:
                return

            if isinstance(value, str):
                output.append(value)
                return

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        output.append(item)
                    elif isinstance(item, dict):
                        for key in ("word", "keyword", "text"):
                            if key in item:
                                output.append(self._safe_str(item.get(key)))
                return

            if isinstance(value, dict):
                for key in ("word", "keyword", "text"):
                    if key in value:
                        output.append(self._safe_str(value.get(key)))
        except Exception:
            return

    def _signal_overlaps_segment(
        self,
        signal: dict[str, Any],
        segment_start: float,
        segment_end: float,
    ) -> bool:
        try:
            signal_start = self._safe_optional_float(
                self._first_value(signal, ("start", "start_seconds", "start_time"))
            )
            signal_end = self._safe_optional_float(
                self._first_value(signal, ("end", "end_seconds", "end_time"))
            )
            center = self._safe_optional_float(
                self._first_value(signal, ("center", "center_seconds", "time"))
            )
            duration = self._safe_optional_float(
                self._first_value(signal, ("duration", "duration_seconds"))
            )

            if signal_start is not None and signal_end is None and duration is not None:
                signal_end = signal_start + max(0.0, duration)

            if signal_start is None and signal_end is None:
                if center is None:
                    return True
                return segment_start <= center <= segment_end

            if signal_start is None:
                signal_start = signal_end

            if signal_end is None:
                signal_end = signal_start

            if signal_start is None or signal_end is None:
                return True

            if signal_end < signal_start:
                signal_start, signal_end = signal_end, signal_start

            return max(segment_start, signal_start) <= min(segment_end, signal_end)
        except Exception:
            return False
