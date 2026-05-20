from dataclasses import dataclass
from typing import Any


SIGNAL_HOOK_IDENTIFICATION = "hook_identification"
SIGNAL_EMOTIONAL_ARC = "emotional_arc"
SIGNAL_DYNAMIC_PACING = "dynamic_pacing"
SIGNAL_REACTION_SHOT = "reaction_shot_placement"
SIGNAL_BUT_THEREFORE = "but_therefore_story"
SIGNAL_FINAL_QUALITY = "final_quality_validator"

_SCORE_FIELDS = (
    "score",
    "signal_score",
    "hook_score",
    "pacing_score",
    "story_score",
)


@dataclass
class TimelineSignalBundle:
    available: bool
    signal_name: str
    signals: list[dict]
    report: dict | None
    warnings: list[str]


class TimelineSignalConsumer:
    def __init__(
        self,
        signals: list[dict] | None = None,
        report: dict | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        self._signals = list(signals or [])
        self._report = dict(report) if isinstance(report, dict) else None
        self._warnings = list(warnings or [])

    @classmethod
    def from_job(cls, job: Any) -> "TimelineSignalConsumer":
        """Liest job.unified_edit_signals sicher aus, ohne bei fehlenden Feldern zu crashen."""
        warnings: list[str] = []

        raw_signals = getattr(job, "unified_edit_signals", [])
        if raw_signals is None:
            raw_signals = []
            warnings.append("missing_unified_edit_signals")

        if not isinstance(raw_signals, list):
            raw_signals = []
            warnings.append("invalid_unified_edit_signals_format")

        signals: list[dict] = []
        for signal in raw_signals:
            if isinstance(signal, dict):
                signals.append(dict(signal))
            else:
                warnings.append("ignored_non_dict_signal")

        raw_report = getattr(job, "unified_edit_signal_report", None)
        report = dict(raw_report) if isinstance(raw_report, dict) else None

        return cls(signals=signals, report=report, warnings=warnings)

    def read(self, signal_name: str) -> TimelineSignalBundle:
        """Gibt alle Signale des Typs signal_name zurück."""
        safe_signal_name = str(signal_name or "").strip()
        matched_signals: list[dict] = []

        for signal in self._signals:
            try:
                if str(signal.get("signal_type") or "").strip() == safe_signal_name:
                    matched_signals.append(signal)
            except Exception:
                continue

        warnings = list(self._warnings)
        if not matched_signals:
            warnings.append(f"missing_signal:{safe_signal_name}")
            return TimelineSignalBundle(
                available=False,
                signal_name=safe_signal_name,
                signals=[],
                report=self._report,
                warnings=warnings,
            )

        return TimelineSignalBundle(
            available=True,
            signal_name=safe_signal_name,
            signals=matched_signals,
            report=self._report,
            warnings=warnings,
        )

    def signals_for_segment(
        self,
        start: float,
        end: float,
        signal_name: str,
    ) -> list[dict]:
        """
        Gibt Signale zurück, die zeitlich mit [start, end] überlappen.

        Overlap-Bedingung:
        signal_start < segment_end AND signal_end > segment_start

        Wenn ein Signal keinen nutzbaren start/end-Zeitstempel hat,
        wird es absichtlich nicht weggefiltert.
        """
        segment_start = _safe_float(start)
        segment_end = _safe_float(end)

        bundle = self.read(signal_name)
        return [
            signal
            for signal in bundle.signals
            if _signal_overlaps_segment(signal, segment_start, segment_end)
        ]

    def best_score_for_segment(
        self,
        start: float,
        end: float,
        signal_name: str,
    ) -> float:
        """Gibt den höchsten Score aus überlappenden Signalen zurück."""
        matching_signals = self.signals_for_segment(start, end, signal_name)
        if not matching_signals:
            return 0.0

        return max(_score_from_signal(signal) for signal in matching_signals)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _safe_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _signal_time(signal: dict, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if key in signal:
            parsed = _safe_optional_float(signal.get(key))
            if parsed is not None:
                return parsed
    return None


def _signal_overlaps_segment(
    signal: dict,
    segment_start: float,
    segment_end: float,
) -> bool:
    signal_start = _signal_time(signal, ("start_seconds", "start", "start_time"))
    signal_end = _signal_time(signal, ("end_seconds", "end", "end_time"))

    if signal_start is None or signal_end is None:
        return True

    return signal_start < segment_end and signal_end > segment_start


def _score_from_signal(signal: dict) -> float:
    for field in _SCORE_FIELDS:
        if field in signal:
            try:
                return float(signal.get(field))
            except Exception:
                return 0.0
    return 0.0
