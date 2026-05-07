from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.timeline_segment import TimelineSegment
from models.universal_moment_soft_decision import (
    UniversalMomentSegmentDecision,
    UniversalMomentSoftDecisionReport,
)
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow


ENGINE = "universal-safe-edge-trim-applier-v1"

MAX_TRIM_PER_EDGE = 0.75
MAX_TRIM_PER_SEGMENT = 1.25
MAX_TOTAL_TRIM_SECONDS = 3.0
MIN_SEGMENT_DURATION = 2.5
FIRST_30S = 30.0
PROTECTED_ROLES = {"hook", "peak", "payoff"}

BORING_THRESHOLD = 0.60
SAFE_PEAK_MAX = 0.35
SAFE_TENSION_MAX = 0.35
SAFE_SPEECH_MAX = 0.35
SAFE_CUT_RISK_MAX = 0.45


@dataclass
class UniversalSafeEdgeTrimSummary:
    trim_candidates_seen: int = 0
    start_trimmed: int = 0
    end_trimmed: int = 0
    skipped_safe_keep: int = 0
    skipped_human_review: int = 0
    skipped_first_30s: int = 0
    skipped_protected_role: int = 0
    skipped_speech_risk: int = 0
    skipped_action_risk: int = 0
    skipped_too_short: int = 0
    total_trimmed_seconds: float = 0.0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    def add_example(self, text: str) -> None:
        if len(self.examples) < 10:
            self.examples.append(text)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trim_candidates_seen": self.trim_candidates_seen,
            "start_trimmed": self.start_trimmed,
            "end_trimmed": self.end_trimmed,
            "skipped_safe_keep": self.skipped_safe_keep,
            "skipped_human_review": self.skipped_human_review,
            "skipped_first_30s": self.skipped_first_30s,
            "skipped_protected_role": self.skipped_protected_role,
            "skipped_speech_risk": self.skipped_speech_risk,
            "skipped_action_risk": self.skipped_action_risk,
            "skipped_too_short": self.skipped_too_short,
            "total_trimmed_seconds": round(self.total_trimmed_seconds, 3),
            "duration_before": round(self.duration_before, 3),
            "duration_after": round(self.duration_after, 3),
            "examples": list(self.examples),
        }


class UniversalSafeEdgeTrimApplier:
    engine = ENGINE

    def apply(
        self,
        selected_segments: list[TimelineSegment],
        *,
        universal_moment_result=None,
        soft_decision_report=None,
    ) -> tuple[list[TimelineSegment], UniversalSafeEdgeTrimSummary]:
        ordered = sorted(
            (s for s in selected_segments if s.end_time > s.start_time),
            key=lambda s: (s.start_time, s.end_time, s.segment_id),
        )
        summary = UniversalSafeEdgeTrimSummary(
            duration_before=round(sum(s.duration for s in ordered), 3)
        )

        if not ordered or soft_decision_report is None:
            summary.duration_after = summary.duration_before
            self._log(summary)
            return ordered, summary

        decisions = self._build_decision_index(soft_decision_report)
        windows = self._parse_windows(universal_moment_result)
        budget_remaining = MAX_TOTAL_TRIM_SECONDS

        for segment in ordered:
            if budget_remaining <= 0.0:
                break

            decision = decisions.get(segment.segment_id)
            if decision is None:
                decision = self._find_decision_by_time(decisions, segment)
            if decision is None:
                continue

            if decision.soft_decision not in {"trim_edges_candidate"}:
                if decision.soft_decision in {"safe_keep", "keep_dominant", "needs_human_review"}:
                    summary.skipped_safe_keep += 1
                continue

            summary.trim_candidates_seen += 1

            if decision.needs_human_review:
                summary.skipped_human_review += 1
                self._add_note(segment, "universal_safe_trim_skipped_reason=needs_human_review")
                continue

            role = str(segment.segment_role or "").lower()
            if role in PROTECTED_ROLES:
                summary.skipped_protected_role += 1
                self._add_note(segment, f"universal_safe_trim_skipped_reason=protected_role:{role}")
                continue

            seg_trim_budget = min(MAX_TRIM_PER_SEGMENT, budget_remaining)
            trimmed_this = 0.0

            start_trim = self._check_start_trim(segment, decision, windows)
            if start_trim > 0.0 and trimmed_this + start_trim <= seg_trim_budget:
                new_start = round(segment.start_time + start_trim, 3)
                if segment.end_time - new_start >= MIN_SEGMENT_DURATION:
                    old_start = segment.start_time
                    segment.start_time = new_start
                    segment.touch()
                    self._add_note(
                        segment,
                        f"universal_safe_start_trim={old_start:.3f}->{new_start:.3f}",
                    )
                    summary.start_trimmed += 1
                    trimmed_this += start_trim
                    summary.add_example(
                        f"{segment.segment_id} start {old_start:.2f}->{new_start:.2f}"
                    )
                else:
                    summary.skipped_too_short += 1

            end_trim = self._check_end_trim(segment, decision, windows)
            if end_trim > 0.0 and trimmed_this + end_trim <= seg_trim_budget:
                new_end = round(segment.end_time - end_trim, 3)
                if new_end - segment.start_time >= MIN_SEGMENT_DURATION:
                    old_end = segment.end_time
                    segment.end_time = new_end
                    segment.touch()
                    self._add_note(
                        segment,
                        f"universal_safe_end_trim={old_end:.3f}->{new_end:.3f}",
                    )
                    summary.end_trimmed += 1
                    trimmed_this += end_trim
                    summary.add_example(
                        f"{segment.segment_id} end {old_end:.2f}->{new_end:.2f}"
                    )
                else:
                    summary.skipped_too_short += 1

            if trimmed_this == 0.0 and start_trim == 0.0 and end_trim == 0.0:
                self._add_note(segment, "universal_safe_trim_skipped_reason=no_safe_edge_found")

            summary.total_trimmed_seconds = round(
                summary.total_trimmed_seconds + trimmed_this, 3
            )
            budget_remaining = round(budget_remaining - trimmed_this, 3)

        ordered = self._final_invariants(ordered)
        summary.duration_after = round(sum(s.duration for s in ordered), 3)
        self._log(summary)
        return ordered, summary

    def _check_start_trim(
        self,
        segment: TimelineSegment,
        decision: UniversalMomentSegmentDecision,
        windows: list[UniversalMomentWindow],
    ) -> float:
        if segment.start_time < FIRST_30S:
            return 0.0

        if decision.protect_pre_context:
            return 0.0

        zone_end = round(segment.start_time + MAX_TRIM_PER_EDGE, 3)
        zone_windows = [
            w for w in windows
            if _overlap_seconds(segment.start_time, zone_end, w.start_seconds, w.end_seconds) > 0.0
        ]

        if not zone_windows:
            return 0.0

        max_boring = max(
            max(w.boring_score, w.private_talk_score, w.menu_wait_score)
            for w in zone_windows
        )
        max_peak = max(w.peak_score for w in zone_windows)
        max_tension = max(w.tension_score for w in zone_windows)
        max_speech = max(w.speech_score for w in zone_windows)
        max_cut_risk = max(w.cut_risk_score for w in zone_windows)
        has_pre_context = any(
            w.needs_pre_context or w.action_context_risk or w.speech_boundary_risk
            for w in zone_windows
        )

        if has_pre_context or max_speech >= SAFE_SPEECH_MAX:
            return 0.0
        if max_peak >= SAFE_PEAK_MAX or max_tension >= SAFE_TENSION_MAX:
            return 0.0
        if max_cut_risk >= SAFE_CUT_RISK_MAX:
            return 0.0
        if max_boring >= BORING_THRESHOLD:
            return MAX_TRIM_PER_EDGE
        return 0.0

    def _check_end_trim(
        self,
        segment: TimelineSegment,
        decision: UniversalMomentSegmentDecision,
        windows: list[UniversalMomentWindow],
    ) -> float:
        if decision.protect_post_context:
            return 0.0

        zone_start = round(segment.end_time - MAX_TRIM_PER_EDGE, 3)
        zone_windows = [
            w for w in windows
            if _overlap_seconds(zone_start, segment.end_time, w.start_seconds, w.end_seconds) > 0.0
        ]

        if not zone_windows:
            return 0.0

        max_boring = max(
            max(w.boring_score, w.private_talk_score, w.menu_wait_score)
            for w in zone_windows
        )
        max_peak = max(w.peak_score for w in zone_windows)
        max_post_reaction = max(w.post_peak_reaction_score for w in zone_windows)
        max_speech = max(w.speech_score for w in zone_windows)
        max_cut_risk = max(w.cut_risk_score for w in zone_windows)
        has_post_context = any(
            w.needs_post_context or w.speech_boundary_risk
            for w in zone_windows
        )

        if has_post_context or max_speech >= SAFE_SPEECH_MAX:
            return 0.0
        if max_peak >= SAFE_PEAK_MAX or max_post_reaction >= SAFE_PEAK_MAX:
            return 0.0
        if max_cut_risk >= SAFE_CUT_RISK_MAX:
            return 0.0
        if max_boring >= BORING_THRESHOLD:
            return MAX_TRIM_PER_EDGE
        return 0.0

    def _build_decision_index(
        self,
        report: UniversalMomentSoftDecisionReport,
    ) -> dict[str, UniversalMomentSegmentDecision]:
        index: dict[str, UniversalMomentSegmentDecision] = {}
        for decision in (report.decisions or []):
            if decision.segment_id:
                index[decision.segment_id] = decision
        return index

    def _find_decision_by_time(
        self,
        decisions: dict[str, UniversalMomentSegmentDecision],
        segment: TimelineSegment,
    ) -> UniversalMomentSegmentDecision | None:
        best: UniversalMomentSegmentDecision | None = None
        best_overlap = 0.0
        for decision in decisions.values():
            overlap = _overlap_seconds(
                segment.start_time, segment.end_time,
                decision.start_time, decision.end_time,
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best = decision
        return best if best_overlap > 0.0 else None

    def _parse_windows(self, universal_moment_result: object) -> list[UniversalMomentWindow]:
        if universal_moment_result is None:
            return []
        if isinstance(universal_moment_result, UniversalMomentResult):
            return [w for w in universal_moment_result.windows if w.end_seconds > w.start_seconds]
        if isinstance(universal_moment_result, dict):
            return self._parse_windows(UniversalMomentResult.from_dict(universal_moment_result))
        raw = getattr(universal_moment_result, "windows", None)
        if raw is None:
            return []
        parsed: list[UniversalMomentWindow] = []
        for w in raw:
            if isinstance(w, UniversalMomentWindow):
                parsed.append(w)
            elif isinstance(w, dict):
                parsed.append(UniversalMomentWindow.from_dict(w))
        return [w for w in parsed if w.end_seconds > w.start_seconds]

    def _final_invariants(self, segments: list[TimelineSegment]) -> list[TimelineSegment]:
        ordered = sorted(
            (s for s in segments if s.end_time > s.start_time),
            key=lambda s: (s.start_time, s.end_time, s.segment_id),
        )
        clean: list[TimelineSegment] = []
        for segment in ordered:
            if clean and segment.start_time < clean[-1].end_time:
                proposed = round(clean[-1].end_time, 3)
                if segment.end_time - proposed >= MIN_SEGMENT_DURATION:
                    segment.start_time = proposed
                    segment.touch()
            clean.append(segment)
        return clean

    def _add_note(self, segment: TimelineSegment, note: str) -> None:
        if note not in segment.notes:
            segment.notes.append(note)

    def _log(self, summary: UniversalSafeEdgeTrimSummary) -> None:
        print(
            "[TIMELINE-UNIVERSAL-SAFE-TRIM] "
            f"candidates={summary.trim_candidates_seen} "
            f"start={summary.start_trimmed} "
            f"end={summary.end_trimmed} "
            f"skipped_safe={summary.skipped_safe_keep} "
            f"skipped_review={summary.skipped_human_review} "
            f"skipped_first30={summary.skipped_first_30s} "
            f"skipped_protected={summary.skipped_protected_role} "
            f"skipped_speech={summary.skipped_speech_risk} "
            f"skipped_action={summary.skipped_action_risk} "
            f"skipped_short={summary.skipped_too_short} "
            f"trimmed_seconds={summary.total_trimmed_seconds:.3f} "
            f"duration_before={summary.duration_before:.3f}s "
            f"duration_after={summary.duration_after:.3f}s"
        )


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))
