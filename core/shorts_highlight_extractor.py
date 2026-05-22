from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from core.llm_brain import LLMBrain, LLMBrainDecision
from core.power_profile import PowerProfile
from core.timeline_signal_consumer import (
    SIGNAL_BUT_THEREFORE,
    SIGNAL_EMOTIONAL_ARC,
    SIGNAL_HOOK_IDENTIFICATION,
    SIGNAL_REACTION_SHOT,
    TimelineSignalConsumer,
)
from models.edit_timeline import EditTimeline
from models.shorts_clip import ShortsClip
from models.timeline_segment import TimelineSegment

logger = logging.getLogger(__name__)

LLM_DISABLED = "LLM_DISABLED"
LLM_SHADOW = "LLM_SHADOW"
LLM_PRIMARY = "LLM_PRIMARY"

SHORTS_MIN_DURATION_SECONDS = 15.0
SHORTS_MAX_DURATION_SECONDS = 60.0

DEFAULT_SHORTS_COUNT = 3

POWER_PROFILE_SHORTS_COUNTS = {
    PowerProfile.ECO: 1,
    PowerProfile.BALANCED: 3,
    PowerProfile.PERFORMANCE: 5,
    PowerProfile.FULL_POWER: 5,
}

PROMPT_TEMPLATE = (
    "Du bist ein YouTube-Shorts-Experte. W?hle die {n} st?rksten Highlight-Momente "
    "f?r YouTube Shorts aus der folgenden Liste aus. Begr?nde jede Auswahl in einem Satz. "
    "Kandidaten: {candidates_json}"
)


@dataclass(frozen=True)
class _ShortsCandidate:
    source_index: int
    source_job_id: str
    start_time: float
    end_time: float
    peak_time: float
    hook_score: float
    transcript_slice: str = ""

    @property
    def planned_duration(self) -> float:
        return round(max(0.0, self.end_time - self.start_time), 3)

    def to_llm_dict(self) -> dict[str, Any]:
        return {
            "index": self.source_index,
            "start": self.start_time,
            "end": self.end_time,
            "duration": self.planned_duration,
            "hook_score": self.hook_score,
            "transcript_slice": self.transcript_slice,
        }


class ShortsHighlightExtractor:
    def __init__(
        self,
        signal_consumer: TimelineSignalConsumer | None = None,
        llm_brain: LLMBrain | None = None,
    ) -> None:
        self.signal_consumer = signal_consumer or TimelineSignalConsumer()
        self.llm_brain = llm_brain or LLMBrain()

    def extract_highlights(
        self,
        timeline: EditTimeline,
        power_profile: str,
        llm_mode: str = LLM_SHADOW,
    ) -> list[ShortsClip]:
        target_count = self._count_for_power_profile(power_profile)
        candidates = self._build_candidates(timeline)

        if not candidates or target_count <= 0:
            return []

        ranked_candidates = sorted(
            candidates,
            key=lambda candidate: (
                candidate.hook_score,
                -candidate.start_time,
            ),
            reverse=True,
        )

        buffer_count = max(target_count * 2, target_count)
        llm_candidates = ranked_candidates[:buffer_count]
        llm_rationale_by_index: dict[int, str] = {}

        normalized_mode = str(llm_mode or LLM_SHADOW).strip().upper()

        if normalized_mode == LLM_SHADOW:
            self._run_llm_shadow_logged_only(
                candidates=llm_candidates,
                target_count=target_count,
            )
            llm_rationale_by_index = {}  # leer; kein Pipeline-Effekt
        elif normalized_mode == LLM_PRIMARY:
            ranked_candidates, llm_rationale_by_index = self._run_llm_primary(
                candidates=llm_candidates,
                fallback_candidates=ranked_candidates,
                target_count=target_count,
            )
        elif normalized_mode != LLM_DISABLED:
            logger.info(
                "[shorts_highlight_extractor] unknown_llm_mode=%s using heuristic only",
                llm_mode,
            )

        selected = self._select_non_overlapping(ranked_candidates, target_count)

        clips: list[ShortsClip] = []
        for clip_index, candidate in enumerate(selected):
            clips.append(
                ShortsClip(
                    source_job_id=candidate.source_job_id,
                    source_start_time=candidate.start_time,
                    source_end_time=candidate.end_time,
                    planned_duration=candidate.planned_duration,
                    reframe_plan=None,
                    hook_score=candidate.hook_score,
                    llm_rationale=llm_rationale_by_index.get(candidate.source_index, ""),
                    status="planned",
                    clip_index=clip_index,
                    output_path="",
                )
            )

        if normalized_mode != LLM_PRIMARY:
            clips.sort(key=lambda clip: clip.hook_score, reverse=True)

        return clips

    def _count_for_power_profile(self, power_profile: str) -> int:
        raw_profile = str(power_profile or "").strip().lower()
        if raw_profile in POWER_PROFILE_SHORTS_COUNTS:
            return POWER_PROFILE_SHORTS_COUNTS[raw_profile]

        logger.info(
            "[shorts_highlight_extractor] unknown_power_profile=%s using_default=%s",
            power_profile,
            DEFAULT_SHORTS_COUNT,
        )
        return DEFAULT_SHORTS_COUNT

    def _build_candidates(self, timeline: EditTimeline) -> list[_ShortsCandidate]:
        segments = sorted(
            list(getattr(timeline, "selected_segments", []) or []),
            key=lambda segment: float(getattr(segment, "start_time", 0.0) or 0.0),
        )
        if not segments:
            return []

        longform_start = min(float(segment.start_time) for segment in segments)
        longform_end = max(float(segment.end_time) for segment in segments)
        candidates: list[_ShortsCandidate] = []

        for index, segment in enumerate(segments):
            raw_start = float(getattr(segment, "start_time", 0.0) or 0.0)
            raw_end = float(getattr(segment, "end_time", raw_start) or raw_start)
            if raw_end <= raw_start:
                continue

            peak_time = self._peak_time_for_segment(segment)
            corrected_start, corrected_end = self._normalize_duration(
                start=raw_start,
                end=raw_end,
                peak_time=peak_time,
                min_bound=longform_start,
                max_bound=longform_end,
            )
            hook_score = self._score_window(
                start=corrected_start,
                end=corrected_end,
                segment=segment,
            )

            candidates.append(
                _ShortsCandidate(
                    source_index=index,
                    source_job_id=str(getattr(segment, "job_id", "") or timeline.job_id),
                    start_time=round(corrected_start, 3),
                    end_time=round(corrected_end, 3),
                    peak_time=round(peak_time, 3),
                    hook_score=round(hook_score, 6),
                    transcript_slice=self._transcript_slice_for_segment(segment),
                )
            )

        return candidates

    def _peak_time_for_segment(self, segment: TimelineSegment) -> float:
        start = float(getattr(segment, "start_time", 0.0) or 0.0)
        end = float(getattr(segment, "end_time", start) or start)
        return start + max(0.0, end - start) / 2.0

    def _normalize_duration(
        self,
        start: float,
        end: float,
        peak_time: float,
        min_bound: float,
        max_bound: float,
    ) -> tuple[float, float]:
        start = max(min_bound, float(start))
        end = min(max_bound, float(end))
        duration = max(0.0, end - start)

        if duration < SHORTS_MIN_DURATION_SECONDS:
            missing = SHORTS_MIN_DURATION_SECONDS - duration
            start -= missing / 2.0
            end += missing / 2.0

            if start < min_bound:
                end += min_bound - start
                start = min_bound
            if end > max_bound:
                start -= end - max_bound
                end = max_bound

            start = max(min_bound, start)
            end = min(max_bound, end)

        duration = max(0.0, end - start)
        if duration > SHORTS_MAX_DURATION_SECONDS:
            half = SHORTS_MAX_DURATION_SECONDS / 2.0
            start = peak_time - half
            end = peak_time + half

            if start < min_bound:
                end += min_bound - start
                start = min_bound
            if end > max_bound:
                start -= end - max_bound
                end = max_bound

            start = max(min_bound, start)
            end = min(max_bound, end)

        return round(start, 3), round(end, 3)

    def _score_window(
        self,
        start: float,
        end: float,
        segment: TimelineSegment,
    ) -> float:
        weighted_signals = (
            (SIGNAL_HOOK_IDENTIFICATION, 0.35),
            (SIGNAL_REACTION_SHOT, 0.25),
            (SIGNAL_EMOTIONAL_ARC, 0.20),
            (SIGNAL_BUT_THEREFORE, 0.20),
        )

        weighted_total = 0.0
        active_weight_total = 0.0

        for signal_name, weight in weighted_signals:
            score = self._safe_signal_score(start, end, signal_name)
            if score > 0.0:
                weighted_total += score * weight
                active_weight_total += weight

        if active_weight_total > 0.0:
            return max(0.0, min(1.0, weighted_total / active_weight_total))

        try:
            return max(0.0, min(1.0, float(getattr(segment, "selection_score", 0.0) or 0.0)))
        except Exception:
            return 0.0

    def _safe_signal_score(self, start: float, end: float, signal_name: str) -> float:
        try:
            value = self.signal_consumer.best_score_for_segment(start, end, signal_name)
            return max(0.0, min(1.0, float(value or 0.0)))
        except Exception:
            return 0.0

    def _transcript_slice_for_segment(self, segment: TimelineSegment) -> str:
        notes = list(getattr(segment, "notes", []) or [])
        text_notes = [str(note) for note in notes if str(note).strip()]
        return " ".join(text_notes)[:500]

    def _select_non_overlapping(
        self,
        ranked_candidates: list[_ShortsCandidate],
        target_count: int,
    ) -> list[_ShortsCandidate]:
        selected: list[_ShortsCandidate] = []

        for candidate in ranked_candidates:
            if len(selected) >= target_count:
                break
            if any(self._overlaps(candidate, chosen) for chosen in selected):
                continue
            selected.append(candidate)

        return selected

    def _overlaps(self, left: _ShortsCandidate, right: _ShortsCandidate) -> bool:
        return left.start_time < right.end_time and left.end_time > right.start_time

    def _run_llm_shadow_logged_only(
        self,
        candidates: list[_ShortsCandidate],
        target_count: int,
    ) -> None:
        decision = self._call_llm(candidates=candidates, target_count=target_count)
        logger.info(
            "[shorts_highlight_extractor] LLM_SHADOW logged_only response=%s",
            decision,
        )
        # Kein Return-Wert. Brain hat gesehen und geloggt, schreibt nicht in Pipeline.

    def _run_llm_primary(
        self,
        candidates: list[_ShortsCandidate],
        fallback_candidates: list[_ShortsCandidate],
        target_count: int,
    ) -> tuple[list[_ShortsCandidate], dict[int, str]]:
        decision = self._call_llm(candidates=candidates, target_count=target_count)
        logger.info("[shorts_highlight_extractor] LLM_PRIMARY response=%s", decision)

        rationale = str(getattr(decision, "reasoning", "") or "")
        rationale_by_index = (
            {candidate.source_index: rationale for candidate in candidates}
            if rationale
            else {}
        )

        recommended_order = getattr(decision, "recommended_order", None)
        if isinstance(recommended_order, list) and recommended_order:
            candidate_by_position = {index: candidate for index, candidate in enumerate(candidates)}
            llm_ranked = [
                candidate_by_position[index]
                for index in recommended_order
                if index in candidate_by_position
            ]
            remaining = [
                candidate
                for candidate in fallback_candidates
                if candidate not in llm_ranked
            ]
            return [*llm_ranked, *remaining], rationale_by_index

        recommended_index = getattr(decision, "recommended_index", None)
        if isinstance(recommended_index, int) and 0 <= recommended_index < len(candidates):
            preferred = candidates[recommended_index]
            remaining = [candidate for candidate in fallback_candidates if candidate != preferred]
            return [preferred, *remaining], rationale_by_index

        return fallback_candidates, rationale_by_index

    def _call_llm(
        self,
        candidates: list[_ShortsCandidate],
        target_count: int,
    ) -> LLMBrainDecision:
        candidates_json = json.dumps(
            [candidate.to_llm_dict() for candidate in candidates],
            ensure_ascii=False,
        )
        prompt = PROMPT_TEMPLATE.format(
            n=target_count,
            candidates_json=candidates_json,
        )

        return self.llm_brain.decide_segment_order(
            segments=[candidate.to_llm_dict() for candidate in candidates],
            arc_hints={
                "prompt": prompt,
                "target_count": target_count,
                "mode": "shorts_highlight_selection",
            },
        )
