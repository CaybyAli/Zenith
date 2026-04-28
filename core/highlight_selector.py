from __future__ import annotations

import uuid

from models.analysis_result import AnalysisResult
from models.edit_signal import EditSignal
from models.highlight_candidate import HighlightCandidate
from models.job import Job
from shared.errors import ValidationError


class HighlightSelector:
    def _make_candidate_id(self) -> str:
        return f"cand_{uuid.uuid4().hex[:12]}"

    def _clamp_score(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _overlaps(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> bool:
        return max(start_a, start_b) < min(end_a, end_b)

    def _overlap_ratio(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> float:
        overlap_start = max(start_a, start_b)
        overlap_end = min(end_a, end_b)

        if overlap_end <= overlap_start:
            return 0.0

        overlap = overlap_end - overlap_start
        shorter = max(0.001, min(end_a - start_a, end_b - start_b))
        return overlap / shorter

    def _build_candidate_kind(self, signal_types: set[str]) -> str:
        if "audio_peak" in signal_types and "motion_peak" in signal_types:
            return "action_peak"
        if "audio_peak" in signal_types:
            return "speech_peak"
        if "motion_peak" in signal_types:
            return "action_peak"
        return "unknown"

    def _score_highlight_window(
        self,
        window_signals: list[EditSignal],
    ) -> tuple[float, list[str]]:
        score = 0.0
        notes: list[str] = []

        signal_types = {signal.signal_type for signal in window_signals}
        tags = {tag for signal in window_signals for tag in signal.tags}

        if "audio_peak" in signal_types:
            score += 0.42
            notes.append("audio_peak_detected")

        if "motion_peak" in signal_types:
            score += 0.34
            notes.append("motion_peak_detected")

        if "audio_activity" in signal_types:
            score += 0.12
            notes.append("audio_activity_present")

        if "motion_activity" in signal_types:
            score += 0.10
            notes.append("motion_activity_present")

        if "audio_peak" in signal_types and "motion_peak" in signal_types:
            score += 0.16
            notes.append("combined_peak_alignment")

        if "intro_zone" in tags:
            score -= 0.05
            notes.append("intro_zone_penalty")

        if "outro_zone" in tags:
            score -= 0.03
            notes.append("outro_zone_penalty")

        return self._clamp_score(score), notes

    def _score_weak_window(
        self,
        window_signals: list[EditSignal],
    ) -> tuple[float, list[str]]:
        score = 0.0
        notes: list[str] = []

        signal_types = {signal.signal_type for signal in window_signals}

        if "silence_zone" in signal_types:
            score += 0.48
            notes.append("silence_zone_detected")

        if "low_motion_zone" in signal_types:
            score += 0.42
            notes.append("low_motion_zone_detected")

        if "silence_zone" in signal_types and "low_motion_zone" in signal_types:
            score += 0.10
            notes.append("combined_low_activity_zone")

        return self._clamp_score(score), notes

    def _dedupe_candidates(
        self,
        candidates: list[HighlightCandidate],
        *,
        overlap_threshold: float = 0.60,
    ) -> list[HighlightCandidate]:
        selected: list[HighlightCandidate] = []

        sorted_candidates = sorted(
            candidates,
            key=lambda candidate: (
                -candidate.highlight_score,
                candidate.start_time,
                candidate.end_time,
            ),
        )

        for candidate in sorted_candidates:
            too_similar = any(
                self._overlap_ratio(
                    candidate.start_time,
                    candidate.end_time,
                    existing.start_time,
                    existing.end_time,
                ) >= overlap_threshold
                for existing in selected
            )

            if not too_similar:
                selected.append(candidate)

        return sorted(
            selected,
            key=lambda candidate: (candidate.start_time, candidate.end_time),
        )

    def select(
        self,
        job: Job,
        analysis_result: AnalysisResult,
        signals: list[EditSignal],
    ) -> dict[str, object]:
        if not signals:
            raise ValidationError("HighlightSelector needs edit signals")

        if analysis_result.duration_seconds <= 0:
            raise ValidationError("HighlightSelector needs positive duration")

        relevant_signals = [
            signal
            for signal in signals
            if signal.signal_type != "duration_context"
        ]

        if not relevant_signals:
            return {
                "highlight_candidates": [],
                "weak_zones": [],
                "summary": {
                    "signal_count": len(signals),
                    "highlight_candidates": 0,
                    "weak_zones": 0,
                },
            }

        highlight_seed_types = {
            "audio_peak",
            "audio_activity",
            "motion_peak",
            "motion_activity",
        }
        weak_seed_types = {
            "silence_zone",
            "low_motion_zone",
        }

        raw_highlights: list[HighlightCandidate] = []
        raw_weak_zones: list[HighlightCandidate] = []

        for seed in relevant_signals:
            if seed.signal_type in highlight_seed_types:
                window_signals = [
                    signal
                    for signal in relevant_signals
                    if signal.signal_type in highlight_seed_types
                    and self._overlaps(
                        seed.start_time,
                        seed.end_time,
                        signal.start_time,
                        signal.end_time,
                    )
                ]

                start_time = min(signal.start_time for signal in window_signals)
                end_time = max(signal.end_time for signal in window_signals)
                highlight_score, notes = self._score_highlight_window(window_signals)

                if highlight_score >= 0.45:
                    signal_types = {signal.signal_type for signal in window_signals}
                    signal_tags = sorted(
                        {tag for signal in window_signals for tag in signal.tags}
                    )
                    confidence = round(
                        sum(signal.confidence for signal in window_signals) / len(window_signals),
                        3,
                    )

                    raw_highlights.append(
                        HighlightCandidate(
                            candidate_id=self._make_candidate_id(),
                            job_id=job.job_id,
                            start_time=round(start_time, 3),
                            end_time=round(end_time, 3),
                            highlight_score=highlight_score,
                            candidate_kind=self._build_candidate_kind(signal_types),
                            confidence=confidence,
                            signal_tags=signal_tags,
                            source="highlight_selector.signals",
                            notes=notes + [f"signals={sorted(signal_types)}"],
                        )
                    )

            if seed.signal_type in weak_seed_types:
                window_signals = [
                    signal
                    for signal in relevant_signals
                    if signal.signal_type in weak_seed_types
                    and self._overlaps(
                        seed.start_time,
                        seed.end_time,
                        signal.start_time,
                        signal.end_time,
                    )
                ]

                start_time = min(signal.start_time for signal in window_signals)
                end_time = max(signal.end_time for signal in window_signals)
                weak_score, notes = self._score_weak_window(window_signals)

                if weak_score >= 0.45:
                    signal_tags = sorted(
                        {tag for signal in window_signals for tag in signal.tags}
                    )
                    confidence = round(
                        sum(signal.confidence for signal in window_signals) / len(window_signals),
                        3,
                    )

                    raw_weak_zones.append(
                        HighlightCandidate(
                            candidate_id=self._make_candidate_id(),
                            job_id=job.job_id,
                            start_time=round(start_time, 3),
                            end_time=round(end_time, 3),
                            highlight_score=weak_score,
                            candidate_kind="drop_zone",
                            confidence=confidence,
                            signal_tags=signal_tags,
                            source="highlight_selector.weak_zones",
                            notes=notes,
                        )
                    )

        highlight_candidates = self._dedupe_candidates(raw_highlights)
        weak_zones = self._dedupe_candidates(raw_weak_zones)

        return {
            "highlight_candidates": highlight_candidates,
            "weak_zones": weak_zones,
            "summary": {
                "signal_count": len(signals),
                "highlight_candidates": len(highlight_candidates),
                "weak_zones": len(weak_zones),
            },
        }