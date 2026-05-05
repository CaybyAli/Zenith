from __future__ import annotations

import uuid
from typing import Iterable

from models.edit_signal import EditSignal
from models.energy_curve_result import EnergyCurvePoint, EnergyCurveResult


class EnergyCurveBuilder:
    engine = "energy-curve-builder-v1"

    POSITIVE_WEIGHTS = {
        "audio_peak": 0.46,
        "motion_peak": 0.42,
        "audio_activity": 0.20,
        "motion_activity": 0.18,
        "hook": 0.36,
        "highlight": 0.44,
        "speech_peak": 0.34,
        "action_peak": 0.40,
    }

    NEGATIVE_WEIGHTS = {
        "silence_zone": 0.46,
        "low_motion_zone": 0.36,
    }

    IGNORED_SIGNAL_TYPES = {
        "duration_context",
    }

    def _make_curve_id(self) -> str:
        return f"energy_curve_{uuid.uuid4().hex[:12]}"

    def _make_point_id(self) -> str:
        return f"energy_point_{uuid.uuid4().hex[:12]}"

    def _safe_float(self, value: object, fallback: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _clamp_score(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _infer_duration(
        self,
        edit_signals: list[EditSignal],
        duration_seconds: float | None,
    ) -> float:
        if duration_seconds is not None and duration_seconds > 0:
            return float(duration_seconds)

        if not edit_signals:
            return 0.0

        return max(0.0, max(float(signal.end_time) for signal in edit_signals))

    def _overlaps_window(
        self,
        signal: EditSignal,
        window_start: float,
        window_end: float,
    ) -> bool:
        return float(signal.start_time) < window_end and float(signal.end_time) > window_start

    def _overlap_factor(
        self,
        signal: EditSignal,
        window_start: float,
        window_end: float,
    ) -> float:
        overlap_start = max(float(signal.start_time), window_start)
        overlap_end = min(float(signal.end_time), window_end)
        overlap_seconds = max(0.0, overlap_end - overlap_start)
        window_seconds = max(0.001, window_end - window_start)

        if overlap_seconds <= 0:
            return 0.0

        return max(0.25, min(1.0, overlap_seconds / window_seconds))

    def _score_signal_for_window(
        self,
        signal: EditSignal,
        window_start: float,
        window_end: float,
    ) -> tuple[float, str]:
        signal_type = str(signal.signal_type)

        if signal_type in self.IGNORED_SIGNAL_TYPES:
            return 0.0, "ignored"

        strength = self._clamp_score(self._safe_float(signal.strength, 0.0))
        confidence = self._clamp_score(self._safe_float(signal.confidence, 0.0))
        confidence_factor = 0.5 + (confidence * 0.5)
        overlap_factor = self._overlap_factor(signal, window_start, window_end)

        if signal_type in self.POSITIVE_WEIGHTS:
            value = (
                self.POSITIVE_WEIGHTS[signal_type]
                * strength
                * confidence_factor
                * overlap_factor
            )
            return value, "positive"

        if signal_type in self.NEGATIVE_WEIGHTS:
            value = -(
                self.NEGATIVE_WEIGHTS[signal_type]
                * max(0.2, strength)
                * confidence_factor
                * overlap_factor
            )
            return value, "negative"

        return 0.0, "unknown"

    def _dominant_signals(
        self,
        scored_signals: list[tuple[str, float]],
        limit: int = 4,
    ) -> list[str]:
        totals: dict[str, float] = {}

        for signal_type, contribution in scored_signals:
            if contribution == 0.0:
                continue
            totals[signal_type] = totals.get(signal_type, 0.0) + abs(contribution)

        return [
            signal_type
            for signal_type, _total in sorted(
                totals.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:limit]
        ]

    def build(
        self,
        *,
        job_id: str,
        edit_signals: Iterable[EditSignal],
        duration_seconds: float | None = None,
        window_seconds: float = 5.0,
        max_peaks: int = 5,
    ) -> EnergyCurveResult:
        signals = sorted(
            list(edit_signals),
            key=lambda signal: (signal.start_time, signal.end_time, signal.signal_type),
        )

        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        duration = self._infer_duration(signals, duration_seconds)

        if duration <= 0:
            return EnergyCurveResult(
                curve_id=self._make_curve_id(),
                job_id=job_id,
                points=[],
                peak_points=[],
                average_energy=0.0,
                max_energy=0.0,
                engine=self.engine,
                notes=["empty_or_zero_duration"],
            )

        points: list[EnergyCurvePoint] = []
        window_start = 0.0

        while window_start < duration:
            window_end = min(window_start + window_seconds, duration)

            window_signals = [
                signal
                for signal in signals
                if self._overlaps_window(signal, window_start, window_end)
            ]

            positive_total = 0.0
            negative_total = 0.0
            scored_signals: list[tuple[str, float]] = []
            source_signal_ids: list[str] = []

            for signal in window_signals:
                contribution, kind = self._score_signal_for_window(
                    signal,
                    window_start,
                    window_end,
                )

                if kind == "positive":
                    positive_total += contribution
                elif kind == "negative":
                    negative_total += abs(contribution)

                if contribution != 0.0:
                    scored_signals.append((signal.signal_type, contribution))
                    source_signal_ids.append(signal.signal_id)

            raw_energy = positive_total - negative_total
            energy_score = self._clamp_score(raw_energy)

            notes: list[str] = []
            if energy_score >= 0.60:
                notes.append("high_energy_window")
            elif energy_score <= 0.10:
                notes.append("low_energy_window")
            else:
                notes.append("medium_energy_window")

            points.append(
                EnergyCurvePoint(
                    point_id=self._make_point_id(),
                    job_id=job_id,
                    start_seconds=round(window_start, 3),
                    end_seconds=round(window_end, 3),
                    energy_score=energy_score,
                    signal_count=len(window_signals),
                    dominant_signals=self._dominant_signals(scored_signals),
                    source_signal_ids=source_signal_ids,
                    notes=notes,
                    metadata={
                        "window_seconds": round(window_seconds, 3),
                        "positive_total": round(positive_total, 3),
                        "negative_total": round(negative_total, 3),
                    },
                )
            )

            window_start += window_seconds

        max_energy = max((point.energy_score for point in points), default=0.0)
        average_energy = round(
            sum(point.energy_score for point in points) / max(1, len(points)),
            3,
        )

        peak_threshold = max(0.35, average_energy + 0.05)
        peak_points = [
            point
            for point in sorted(points, key=lambda item: item.energy_score, reverse=True)
            if point.energy_score >= peak_threshold and point.energy_score > 0.0
        ][:max_peaks]

        return EnergyCurveResult(
            curve_id=self._make_curve_id(),
            job_id=job_id,
            points=points,
            peak_points=peak_points,
            average_energy=average_energy,
            max_energy=max_energy,
            engine=self.engine,
            notes=[
                f"window_seconds={window_seconds}",
                f"points={len(points)}",
                f"peaks={len(peak_points)}",
            ],
        )
