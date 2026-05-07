from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models.timeline_segment import TimelineSegment
from models.universal_context_audit import (
    ENGINE,
    UniversalContextAuditReport,
    UniversalSegmentContextAudit,
)
from models.universal_moment_debug_report import (
    UniversalMomentDebugReport,
    UniversalMomentSegmentDebug,
)
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow
from models.universal_moment_soft_decision import (
    UniversalMomentSegmentDecision,
    UniversalMomentSoftDecisionReport,
)
from models.universal_role_decision_audit import (
    UniversalRoleDecisionAuditReport,
    UniversalRoleDecisionSegmentAudit,
)


FIRST_30S = 30.0
PROTECTED_ROLES = {"hook", "peak", "payoff"}
EDGE_SECONDS = 0.85


@dataclass
class _SignalStats:
    segment_id: str = ""
    role: str = "unknown"
    start: float = 0.0
    end: float = 0.001
    peak: float = 0.0
    tension: float = 0.0
    post_reaction: float = 0.0
    action: float = 0.0
    speech: float = 0.0
    private: float = 0.0
    menu: float = 0.0
    boring: float = 0.0
    cut: float = 0.0
    zoom: float = 0.0
    keep: float = 0.0
    remove: float = 0.0
    conflict: float = 0.0
    pre_context: float = 0.0
    post_context: float = 0.0
    soft_decision: str = "unknown"
    role_alignment: str = "unknown"
    protected: bool = False
    first_30s: bool = False


class UniversalContextAuditor:
    engine = ENGINE

    def build(
        self,
        *,
        job_id: str,
        timeline_segments: list[TimelineSegment],
        debug_report=None,
        soft_decision_report=None,
        role_decision_audit_report=None,
        universal_moment_result=None,
    ) -> UniversalContextAuditReport:
        segments = sorted(
            [
                segment
                for segment in (timeline_segments or [])
                if getattr(segment, "end_time", 0.0) > getattr(segment, "start_time", 0.0)
            ],
            key=lambda item: (item.start_time, item.end_time, item.segment_id),
        )
        parsed_debug = self._debug_report(debug_report, job_id=job_id)
        parsed_soft = self._soft_report(soft_decision_report, job_id=job_id)
        parsed_role = self._role_report(role_decision_audit_report, job_id=job_id)
        windows = self._windows(universal_moment_result)

        debug_by_id = {
            item.segment_id: item
            for item in parsed_debug.segments
            if item.segment_id
        }
        soft_by_id = {
            item.segment_id: item
            for item in parsed_soft.decisions
            if item.segment_id
        }
        role_by_id = {
            item.segment_id: item
            for item in parsed_role.segments
            if item.segment_id
        }

        audits: list[UniversalSegmentContextAudit] = []
        for index, segment in enumerate(segments):
            previous_segment = segments[index - 1] if index > 0 else None
            next_segment = segments[index + 1] if index < len(segments) - 1 else None
            audits.append(
                self._build_segment_audit(
                    index=index,
                    segment=segment,
                    previous_segment=previous_segment,
                    next_segment=next_segment,
                    debug=self._matching_debug(segment, debug_by_id, parsed_debug.segments),
                    soft=self._matching_soft(segment, soft_by_id, parsed_soft.decisions),
                    role_audit=self._matching_role(segment, role_by_id, parsed_role.segments),
                    previous_debug=(
                        self._matching_debug(previous_segment, debug_by_id, parsed_debug.segments)
                        if previous_segment is not None
                        else None
                    ),
                    next_debug=(
                        self._matching_debug(next_segment, debug_by_id, parsed_debug.segments)
                        if next_segment is not None
                        else None
                    ),
                    previous_soft=(
                        self._matching_soft(previous_segment, soft_by_id, parsed_soft.decisions)
                        if previous_segment is not None
                        else None
                    ),
                    next_soft=(
                        self._matching_soft(next_segment, soft_by_id, parsed_soft.decisions)
                        if next_segment is not None
                        else None
                    ),
                    windows=windows,
                )
            )

        report = UniversalContextAuditReport(
            job_id=str(job_id or parsed_debug.job_id or parsed_soft.job_id or ""),
            engine=self.engine,
            segments=audits,
        )
        self._log(report)
        return report

    def _build_segment_audit(
        self,
        *,
        index: int,
        segment: TimelineSegment,
        previous_segment: TimelineSegment | None,
        next_segment: TimelineSegment | None,
        debug: UniversalMomentSegmentDebug | None,
        soft: UniversalMomentSegmentDecision | None,
        role_audit: UniversalRoleDecisionSegmentAudit | None,
        previous_debug: UniversalMomentSegmentDebug | None,
        next_debug: UniversalMomentSegmentDebug | None,
        previous_soft: UniversalMomentSegmentDecision | None,
        next_soft: UniversalMomentSegmentDecision | None,
        windows: list[UniversalMomentWindow],
    ) -> UniversalSegmentContextAudit:
        current_windows = self._overlapping_windows(segment.start_time, segment.end_time, windows)
        previous_windows = (
            self._overlapping_windows(previous_segment.start_time, previous_segment.end_time, windows)
            if previous_segment is not None
            else []
        )
        next_windows = (
            self._overlapping_windows(next_segment.start_time, next_segment.end_time, windows)
            if next_segment is not None
            else []
        )

        current = self._stats(
            segment=segment,
            debug=debug,
            soft=soft,
            role_audit=role_audit,
            windows=current_windows,
        )
        previous = (
            self._stats(
                segment=previous_segment,
                debug=previous_debug,
                soft=previous_soft,
                role_audit=None,
                windows=previous_windows,
            )
            if previous_segment is not None
            else None
        )
        next_stats = (
            self._stats(
                segment=next_segment,
                debug=next_debug,
                soft=next_soft,
                role_audit=None,
                windows=next_windows,
            )
            if next_segment is not None
            else None
        )

        previous_relation, previous_strength = self._previous_relation(
            previous=previous,
            current=current,
            next_stats=next_stats,
        )
        next_relation, next_strength = self._next_relation(
            previous=previous,
            current=current,
            next_stats=next_stats,
        )

        previous_boundary_type = self._boundary_type(
            left=previous,
            right=current,
            edge_time=current.start,
            relation=previous_relation,
            edge_windows=self._edge_windows(current.start, windows),
        )
        next_boundary_type = self._boundary_type(
            left=current,
            right=next_stats,
            edge_time=current.end,
            relation=next_relation,
            edge_windows=self._edge_windows(current.end, windows),
        )
        previous_boundary_risk = previous_boundary_type not in {"clean", "unknown"}
        next_boundary_risk = next_boundary_type not in {"clean", "unknown"}

        neighbor_keep_score = self._score(
            max(
                previous.keep if previous else 0.0,
                next_stats.keep if next_stats else 0.0,
                previous.action if previous else 0.0,
                next_stats.action if next_stats else 0.0,
            )
        )
        neighbor_remove_score = self._score(
            max(
                previous.remove if previous else 0.0,
                next_stats.remove if next_stats else 0.0,
                previous.private if previous else 0.0,
                next_stats.private if next_stats else 0.0,
                previous.boring if previous else 0.0,
                next_stats.boring if next_stats else 0.0,
            )
        )
        setup_score = self._setup_score(current=current, next_stats=next_stats)
        payoff_score = self._payoff_score(previous=previous, current=current)
        start_trim_ok, end_trim_ok, edge_trim_safety = self._edge_trim_diagnosis(
            current=current,
            current_windows=current_windows,
            previous_relation=previous_relation,
            next_relation=next_relation,
            previous_boundary_type=previous_boundary_type,
            next_boundary_type=next_boundary_type,
        )
        context_conflict_score = self._context_conflict_score(
            current=current,
            neighbor_keep_score=neighbor_keep_score,
            neighbor_remove_score=neighbor_remove_score,
            previous_boundary_risk=previous_boundary_risk,
            next_boundary_risk=next_boundary_risk,
            previous_relation=previous_relation,
            next_relation=next_relation,
        )

        context_decision, reasons, warnings, notes = self._context_decision(
            current=current,
            previous=previous,
            next_stats=next_stats,
            previous_relation=previous_relation,
            next_relation=next_relation,
            previous_boundary_risk=previous_boundary_risk,
            next_boundary_risk=next_boundary_risk,
            previous_boundary_type=previous_boundary_type,
            next_boundary_type=next_boundary_type,
            setup_score=setup_score,
            payoff_score=payoff_score,
            context_conflict_score=context_conflict_score,
            start_trim_ok=start_trim_ok,
            end_trim_ok=end_trim_ok,
        )

        should_merge_with_previous = previous_relation in {
            "setup_context",
            "action_continuation",
            "speech_continuation",
            "private_talk_continuation",
            "menu_continuation",
            "boring_continuation",
        }
        should_merge_with_next = next_relation in {
            "payoff_context",
            "action_continuation",
            "speech_continuation",
            "private_talk_continuation",
            "menu_continuation",
            "boring_continuation",
        }
        should_protect_previous_boundary = previous_boundary_risk or previous_relation in {
            "setup_context",
            "action_continuation",
            "speech_continuation",
        }
        should_protect_next_boundary = next_boundary_risk or next_relation in {
            "payoff_context",
            "action_continuation",
            "speech_continuation",
        }

        return UniversalSegmentContextAudit(
            segment_id=segment.segment_id,
            segment_role=segment.segment_role,
            start_time=segment.start_time,
            end_time=segment.end_time,
            duration_seconds=segment.duration,
            segment_index=index,
            previous_segment_id=previous_segment.segment_id if previous_segment is not None else None,
            next_segment_id=next_segment.segment_id if next_segment is not None else None,
            previous_relation=previous_relation,
            next_relation=next_relation,
            previous_boundary_risk=previous_boundary_risk,
            next_boundary_risk=next_boundary_risk,
            previous_boundary_type=previous_boundary_type,
            next_boundary_type=next_boundary_type,
            previous_context_strength=previous_strength,
            next_context_strength=next_strength,
            setup_score=setup_score,
            payoff_score=payoff_score,
            neighbor_keep_score=neighbor_keep_score,
            neighbor_remove_score=neighbor_remove_score,
            context_conflict_score=context_conflict_score,
            edge_trim_safety_score=edge_trim_safety,
            context_decision=context_decision,
            should_merge_with_previous=should_merge_with_previous,
            should_merge_with_next=should_merge_with_next,
            should_protect_previous_boundary=should_protect_previous_boundary,
            should_protect_next_boundary=should_protect_next_boundary,
            can_consider_start_trim_later=start_trim_ok,
            can_consider_end_trim_later=end_trim_ok,
            should_not_auto_remove=True,
            reasons=self._dedupe(reasons),
            warnings=self._dedupe(warnings),
            notes=self._dedupe(notes),
        )

    def _stats(
        self,
        *,
        segment: TimelineSegment,
        debug: UniversalMomentSegmentDebug | None,
        soft: UniversalMomentSegmentDecision | None,
        role_audit: UniversalRoleDecisionSegmentAudit | None,
        windows: list[UniversalMomentWindow],
    ) -> _SignalStats:
        role = str(getattr(segment, "segment_role", "unknown") or "unknown").lower()
        peak = self._score(max(self._field(debug, "avg_peak_score"), self._avg(w.peak_score for w in windows)))
        tension = self._score(max(self._field(debug, "avg_tension_score"), self._avg(w.tension_score for w in windows)))
        post = self._score(max(self._field(debug, "avg_post_reaction_score"), self._avg(w.post_peak_reaction_score for w in windows)))
        visual_action = self._avg(max(w.visual_action_score, w.gameplay_motion_score) for w in windows)
        action = self._score(max(peak, tension, post, visual_action))
        speech = self._score(max(self._field(debug, "avg_speech_score"), self._avg(w.speech_score for w in windows)))
        private = self._score(max(self._field(debug, "avg_private_talk_score"), self._avg(w.private_talk_score for w in windows)))
        menu = self._score(max(self._field(debug, "avg_menu_wait_score"), self._avg(w.menu_wait_score for w in windows)))
        boring = self._score(max(self._field(debug, "avg_boring_score"), self._avg(max(w.boring_score, w.dead_time_score) for w in windows)))
        cut = self._score(max(self._field(debug, "avg_cut_risk_score"), self._avg(w.cut_risk_score for w in windows)))
        zoom = self._score(max(self._field(debug, "avg_zoom_risk_score"), self._avg(w.zoom_risk_score for w in windows)))
        keep = self._score(
            max(
                self._field(debug, "avg_keep_score"),
                self._field(soft, "keep_confidence"),
                peak,
                tension,
                post,
                0.62 if bool(getattr(debug, "has_keep_signal", False)) else 0.0,
            )
        )
        remove = self._score(
            max(
                self._field(debug, "avg_remove_score"),
                self._field(soft, "remove_confidence"),
                private,
                menu,
                boring,
                0.62 if bool(getattr(debug, "has_remove_signal", False)) else 0.0,
            )
        )
        pre_context = self._score(max(tension, self._max(0.72 for w in windows if w.needs_pre_context)))
        post_context = self._score(max(post, self._max(0.72 for w in windows if w.needs_post_context)))
        return _SignalStats(
            segment_id=str(getattr(segment, "segment_id", "") or ""),
            role=role,
            start=self._seconds(getattr(segment, "start_time", 0.0)),
            end=self._seconds(getattr(segment, "end_time", 0.0)),
            peak=peak,
            tension=tension,
            post_reaction=post,
            action=action,
            speech=speech,
            private=private,
            menu=menu,
            boring=boring,
            cut=cut,
            zoom=zoom,
            keep=keep,
            remove=remove,
            conflict=self._score(self._field(soft, "conflict_score")),
            pre_context=pre_context,
            post_context=post_context,
            soft_decision=str(getattr(soft, "soft_decision", "unknown") or "unknown"),
            role_alignment=str(getattr(role_audit, "role_decision_alignment", "unknown") or "unknown"),
            protected=role in PROTECTED_ROLES,
            first_30s=self._seconds(getattr(segment, "start_time", 0.0)) < FIRST_30S,
        )

    def _previous_relation(
        self,
        *,
        previous: _SignalStats | None,
        current: _SignalStats,
        next_stats: _SignalStats | None,
    ) -> tuple[str, float]:
        if previous is None:
            return "none", 0.0
        previous_setup = previous.tension >= 0.55 or previous.pre_context >= 0.55 or (
            previous.keep >= 0.62 and previous.peak < 0.55
        )
        current_or_next_peak = self._is_peakish(current) or (
            next_stats is not None and self._is_peakish(next_stats)
        )
        if previous_setup and current_or_next_peak:
            return "setup_context", self._score(max(previous.tension, previous.pre_context, current.peak, current.post_reaction))
        if self._both_action(previous, current):
            return "action_continuation", self._score(min(previous.action, current.action))
        if self._both_speech(previous, current):
            return "speech_continuation", self._score(min(previous.speech, current.speech))
        if previous.private >= 0.55 and current.private >= 0.55:
            return "private_talk_continuation", self._score(min(previous.private, current.private))
        if self._menu_like(previous) and self._menu_like(current):
            return "menu_continuation", self._score(min(max(previous.menu, previous.private), max(current.menu, current.private)))
        if self._boring_like(previous) and self._boring_like(current):
            return "boring_continuation", self._score(min(previous.boring, current.boring, previous.remove, current.remove))
        return "weak_relation", self._weak_strength(previous, current)

    def _next_relation(
        self,
        *,
        previous: _SignalStats | None,
        current: _SignalStats,
        next_stats: _SignalStats | None,
    ) -> tuple[str, float]:
        del previous
        if next_stats is None:
            return "none", 0.0
        current_setup = current.tension >= 0.52 or current.pre_context >= 0.52 or (
            current.keep >= 0.55 and current.peak < 0.55 and next_stats.peak >= 0.55
        )
        next_payoff = self._is_peakish(next_stats)
        if current_setup and next_payoff:
            return "payoff_context", self._score(max(current.tension, current.pre_context, next_stats.peak, next_stats.post_reaction))
        if self._both_action(current, next_stats):
            return "action_continuation", self._score(min(current.action, next_stats.action))
        if self._both_speech(current, next_stats):
            return "speech_continuation", self._score(min(current.speech, next_stats.speech))
        if current.private >= 0.55 and next_stats.private >= 0.55:
            return "private_talk_continuation", self._score(min(current.private, next_stats.private))
        if self._menu_like(current) and self._menu_like(next_stats):
            return "menu_continuation", self._score(min(max(current.menu, current.private), max(next_stats.menu, next_stats.private)))
        if self._boring_like(current) and self._boring_like(next_stats):
            return "boring_continuation", self._score(min(current.boring, next_stats.boring, current.remove, next_stats.remove))
        return "weak_relation", self._weak_strength(current, next_stats)

    def _boundary_type(
        self,
        *,
        left: _SignalStats | None,
        right: _SignalStats | None,
        edge_time: float,
        relation: str,
        edge_windows: list[UniversalMomentWindow],
    ) -> str:
        if left is None or right is None:
            return "clean"
        edge_speech = self._max(
            max(w.speech_score, w.cut_risk_score if w.speech_boundary_risk else 0.0)
            for w in edge_windows
        )
        edge_action = self._max(
            max(
                w.peak_score,
                w.tension_score,
                w.visual_action_score,
                w.gameplay_motion_score,
                0.66 if w.action_context_risk else 0.0,
            )
            for w in edge_windows
        )
        edge_zoom = self._max(
            max(w.zoom_risk_score, 0.66 if w.zoom_boundary_risk else 0.0)
            for w in edge_windows
        )
        gap = max(0.0, right.start - left.end)
        if edge_speech >= 0.55 or (left.speech >= 0.55 and right.speech >= 0.55 and gap < 0.75):
            return "speech_cut_risk"
        if edge_action >= 0.60 or (left.action >= 0.60 and right.action >= 0.60 and gap < 0.75):
            return "action_cut_risk"
        if edge_zoom >= 0.55 or left.zoom >= 0.55 or right.zoom >= 0.55:
            return "zoom_cut_risk"
        if (self._menu_like(left) and right.action >= 0.60) or (left.action >= 0.60 and self._menu_like(right)):
            return "menu_jump"
        if gap < 0.5 and relation in {"weak_relation", "unknown"}:
            return "micro_gap"
        semantic_jump = (
            (left.action >= 0.60 and self._boring_like(right))
            or (self._boring_like(left) and right.action >= 0.60)
            or (left.speech >= 0.55 and self._menu_like(right) and right.speech < 0.35)
        )
        if semantic_jump or gap >= 1.5:
            return "hard_jump"
        return "clean"

    def _setup_score(self, *, current: _SignalStats, next_stats: _SignalStats | None) -> float:
        if next_stats is None:
            return 0.0
        return self._score(
            (max(current.tension, current.pre_context, current.keep) * 0.52)
            + (max(next_stats.peak, next_stats.post_reaction, 0.62 if next_stats.role == "peak" else 0.0) * 0.48)
        )

    def _payoff_score(self, *, previous: _SignalStats | None, current: _SignalStats) -> float:
        if previous is None:
            return self._score(max(current.peak, current.post_reaction) * 0.55)
        return self._score(
            (max(previous.tension, previous.pre_context, previous.keep) * 0.42)
            + (max(current.peak, current.post_reaction, 0.62 if current.role in {"peak", "payoff"} else 0.0) * 0.58)
        )

    def _context_conflict_score(
        self,
        *,
        current: _SignalStats,
        neighbor_keep_score: float,
        neighbor_remove_score: float,
        previous_boundary_risk: bool,
        next_boundary_risk: bool,
        previous_relation: str,
        next_relation: str,
    ) -> float:
        boundary_bonus = 0.16 if previous_boundary_risk or next_boundary_risk else 0.0
        relation_conflict = 0.12 if (
            neighbor_keep_score >= 0.55
            and neighbor_remove_score >= 0.55
            and previous_relation in {"weak_relation", "none"}
            and next_relation in {"weak_relation", "none"}
        ) else 0.0
        return self._score(
            max(
                current.conflict,
                min(current.keep, current.remove) * 0.62,
                min(neighbor_keep_score, neighbor_remove_score) * 0.48,
            )
            + boundary_bonus
            + relation_conflict
        )

    def _edge_trim_diagnosis(
        self,
        *,
        current: _SignalStats,
        current_windows: list[UniversalMomentWindow],
        previous_relation: str,
        next_relation: str,
        previous_boundary_type: str,
        next_boundary_type: str,
    ) -> tuple[bool, bool, float]:
        if current.first_30s or current.protected or current.soft_decision != "needs_human_review":
            return False, False, 0.0
        low_action = current.peak < 0.50 and current.tension < 0.50
        if not low_action:
            return False, False, 0.0
        start = self._edge_profile(current.start, current_windows)
        end = self._edge_profile(current.end, current_windows)
        start_ok = (
            previous_relation in {"none", "weak_relation", "unknown"}
            and previous_boundary_type in {"clean", "micro_gap", "hard_jump"}
            and start["remove_edge"] >= 0.62
            and start["protect_edge"] < 0.45
        )
        end_ok = (
            next_relation in {"none", "weak_relation", "unknown"}
            and next_boundary_type in {"clean", "micro_gap", "hard_jump"}
            and end["remove_edge"] >= 0.62
            and end["protect_edge"] < 0.45
        )
        if start_ok and end_ok:
            safety = min(start["remove_edge"], end["remove_edge"], 0.72)
        elif start_ok:
            safety = min(start["remove_edge"], 0.66)
        elif end_ok:
            safety = min(end["remove_edge"], 0.66)
        else:
            safety = 0.0
        return start_ok, end_ok, self._score(safety)

    def _edge_profile(self, edge_time: float, windows: list[UniversalMomentWindow]) -> dict[str, float]:
        edge_windows = self._edge_windows(edge_time, windows)
        remove_edge = self._max(
            max(w.private_talk_score, w.boring_score, w.menu_wait_score, w.dead_time_score)
            for w in edge_windows
        )
        protect_edge = self._max(
            max(
                w.speech_score,
                w.peak_score,
                w.tension_score,
                w.cut_risk_score,
                w.zoom_risk_score,
                0.66 if w.speech_boundary_risk or w.action_context_risk else 0.0,
            )
            for w in edge_windows
        )
        return {"remove_edge": remove_edge, "protect_edge": protect_edge}

    def _context_decision(
        self,
        *,
        current: _SignalStats,
        previous: _SignalStats | None,
        next_stats: _SignalStats | None,
        previous_relation: str,
        next_relation: str,
        previous_boundary_risk: bool,
        next_boundary_risk: bool,
        previous_boundary_type: str,
        next_boundary_type: str,
        setup_score: float,
        payoff_score: float,
        context_conflict_score: float,
        start_trim_ok: bool,
        end_trim_ok: bool,
    ) -> tuple[str, list[str], list[str], list[str]]:
        reasons: list[str] = []
        warnings: list[str] = []
        notes: list[str] = []

        decision = "unknown"
        if previous_relation == "setup_context" and self._is_peakish(current):
            decision = "keep_as_payoff"
            reasons.append("KEEP: previous segment behaves like setup for current payoff/peak.")
        elif next_relation == "payoff_context" and setup_score >= 0.50:
            decision = "keep_as_setup"
            reasons.append("KEEP: current segment sets up the next peak/payoff.")
        elif previous_relation in {"action_continuation", "speech_continuation"} or next_relation in {"action_continuation", "speech_continuation"}:
            decision = "keep_context_chain"
            reasons.append("KEEP: neighbor relation forms action/speech context chain.")
        elif self._private_menu_block(previous=previous, current=current, next_stats=next_stats):
            decision = "private_menu_block_candidate"
            reasons.append("DIAGNOSIS: previous/current/next are dominated by private/menu signals.")
        elif previous_boundary_risk or next_boundary_risk:
            decision = "boundary_protect"
            reasons.append("PROTECT: boundary diagnosis indicates cut risk.")
        elif self._boring_bridge(previous=previous, current=current, next_stats=next_stats):
            decision = "boring_bridge_candidate"
            reasons.append("DIAGNOSIS: current segment is boring/remove-heavy without strong neighbor context.")
        elif start_trim_ok or end_trim_ok:
            decision = "edge_trim_candidate"
            reasons.append("DIAGNOSIS: only weakly related private/boring edge may be trimmable later.")
        elif current.soft_decision == "needs_human_review" or context_conflict_score >= 0.45:
            decision = "needs_human_review"
            reasons.append("REVIEW: context conflict remains too high for automatic classification.")
        elif current.soft_decision == "safe_keep" and not previous_boundary_risk and not next_boundary_risk:
            decision = "safe"
            reasons.append("SAFE: current safe_keep has clean neighbor boundaries.")
        else:
            decision = "needs_human_review"
            reasons.append("REVIEW: neighbor context does not produce a confident diagnosis.")

        if current.first_30s:
            warnings.append("first_30s_context_protection")
            notes.append("first_30s_context_protection_active")
            if decision in {"private_menu_block_candidate", "boring_bridge_candidate", "edge_trim_candidate"}:
                decision = "needs_human_review"
                reasons.append("SAFETY: first 30 seconds stay manual-review protected.")

        if current.protected:
            warnings.append("protected_segment_role")
            if decision in {"private_menu_block_candidate", "boring_bridge_candidate", "edge_trim_candidate"}:
                decision = "boundary_protect" if (previous_boundary_risk or next_boundary_risk) else "keep_context_chain"
                reasons.append("SAFETY: protected role cannot become remove/trim-oriented context candidate.")

        if previous_boundary_risk:
            notes.append(f"previous_boundary={previous_boundary_type}")
        if next_boundary_risk:
            notes.append(f"next_boundary={next_boundary_type}")
        if current.role_alignment not in {"unknown", "aligned", "safe_keep_correct"}:
            notes.append(f"role_audit_alignment={current.role_alignment}")
        return decision, reasons, warnings, notes

    def _private_menu_block(
        self,
        *,
        previous: _SignalStats | None,
        current: _SignalStats,
        next_stats: _SignalStats | None,
    ) -> bool:
        items = [item for item in (previous, current, next_stats) if item is not None]
        if len(items) < 2:
            return False
        private_menu_count = sum(max(item.private, item.menu) >= 0.55 for item in items)
        strong_keep_count = sum(max(item.peak, item.tension, item.post_reaction) >= 0.55 for item in items)
        return private_menu_count >= 2 and strong_keep_count == 0 and current.remove >= 0.50

    def _boring_bridge(
        self,
        *,
        previous: _SignalStats | None,
        current: _SignalStats,
        next_stats: _SignalStats | None,
    ) -> bool:
        if max(current.boring, current.remove) < 0.60:
            return False
        if max(current.peak, current.tension, current.speech) >= 0.50:
            return False
        neighbor_context = max(
            previous.keep if previous else 0.0,
            previous.action if previous else 0.0,
            next_stats.keep if next_stats else 0.0,
            next_stats.action if next_stats else 0.0,
        )
        return neighbor_context < 0.55

    def _is_peakish(self, item: _SignalStats) -> bool:
        return item.role in {"peak", "payoff"} or max(item.peak, item.post_reaction) >= 0.55

    def _both_action(self, left: _SignalStats, right: _SignalStats) -> bool:
        return left.action >= 0.55 and right.action >= 0.55

    def _both_speech(self, left: _SignalStats, right: _SignalStats) -> bool:
        return left.speech >= 0.55 and right.speech >= 0.55

    def _menu_like(self, item: _SignalStats) -> bool:
        return max(item.menu, item.private) >= 0.55 and item.action < 0.55

    def _boring_like(self, item: _SignalStats) -> bool:
        return max(item.boring, item.remove) >= 0.60 and max(item.peak, item.tension) < 0.50

    def _weak_strength(self, left: _SignalStats, right: _SignalStats) -> float:
        return self._score(
            max(
                min(left.action, right.action),
                min(left.speech, right.speech),
                min(max(left.private, left.menu), max(right.private, right.menu)),
                min(left.boring, right.boring),
            )
            * 0.42
        )

    def _debug_report(self, report: Any, *, job_id: str) -> UniversalMomentDebugReport:
        if isinstance(report, UniversalMomentDebugReport):
            return report
        if isinstance(report, dict):
            return UniversalMomentDebugReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return UniversalMomentDebugReport.from_dict(report.to_dict())
        return UniversalMomentDebugReport(job_id=str(job_id or ""))

    def _soft_report(self, report: Any, *, job_id: str) -> UniversalMomentSoftDecisionReport:
        if isinstance(report, UniversalMomentSoftDecisionReport):
            return report
        if isinstance(report, dict):
            return UniversalMomentSoftDecisionReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return UniversalMomentSoftDecisionReport.from_dict(report.to_dict())
        return UniversalMomentSoftDecisionReport(job_id=str(job_id or ""))

    def _role_report(self, report: Any, *, job_id: str) -> UniversalRoleDecisionAuditReport:
        if isinstance(report, UniversalRoleDecisionAuditReport):
            return report
        if isinstance(report, dict):
            return UniversalRoleDecisionAuditReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return UniversalRoleDecisionAuditReport.from_dict(report.to_dict())
        return UniversalRoleDecisionAuditReport(job_id=str(job_id or ""))

    def _matching_debug(
        self,
        segment: TimelineSegment,
        by_id: dict[str, UniversalMomentSegmentDebug],
        all_items: list[UniversalMomentSegmentDebug],
    ) -> UniversalMomentSegmentDebug | None:
        if segment.segment_id in by_id:
            return by_id[segment.segment_id]
        return self._find_by_time(all_items, segment)

    def _matching_soft(
        self,
        segment: TimelineSegment,
        by_id: dict[str, UniversalMomentSegmentDecision],
        all_items: list[UniversalMomentSegmentDecision],
    ) -> UniversalMomentSegmentDecision | None:
        if segment.segment_id in by_id:
            return by_id[segment.segment_id]
        return self._find_by_time(all_items, segment)

    def _matching_role(
        self,
        segment: TimelineSegment,
        by_id: dict[str, UniversalRoleDecisionSegmentAudit],
        all_items: list[UniversalRoleDecisionSegmentAudit],
    ) -> UniversalRoleDecisionSegmentAudit | None:
        if segment.segment_id in by_id:
            return by_id[segment.segment_id]
        return self._find_by_time(all_items, segment)

    def _find_by_time(self, items: list[Any], segment: TimelineSegment) -> Any | None:
        best = None
        best_overlap = 0.0
        for item in items:
            overlap = self._overlap_seconds(
                segment.start_time,
                segment.end_time,
                self._seconds(getattr(item, "start_time", 0.0)),
                self._seconds(getattr(item, "end_time", 0.0)),
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best = item
        return best if best_overlap > 0.0 else None

    def _windows(self, universal_moment_result: object) -> list[UniversalMomentWindow]:
        if universal_moment_result is None:
            return []
        if isinstance(universal_moment_result, UniversalMomentResult):
            return [w for w in universal_moment_result.windows if w.end_seconds > w.start_seconds]
        if isinstance(universal_moment_result, dict):
            return self._windows(UniversalMomentResult.from_dict(universal_moment_result))
        raw = getattr(universal_moment_result, "windows", None)
        if raw is None:
            return []
        parsed: list[UniversalMomentWindow] = []
        for item in raw:
            if isinstance(item, UniversalMomentWindow):
                parsed.append(item)
            elif isinstance(item, dict):
                parsed.append(UniversalMomentWindow.from_dict(item))
        return sorted(
            (item for item in parsed if item.end_seconds > item.start_seconds),
            key=lambda item: (item.start_seconds, item.end_seconds, item.window_id),
        )

    def _overlapping_windows(
        self,
        start: float,
        end: float,
        windows: list[UniversalMomentWindow],
    ) -> list[UniversalMomentWindow]:
        return [
            window
            for window in windows
            if self._overlap_seconds(start, end, window.start_seconds, window.end_seconds) > 0.0
        ]

    def _edge_windows(
        self,
        edge_time: float,
        windows: list[UniversalMomentWindow],
    ) -> list[UniversalMomentWindow]:
        start = max(0.0, edge_time - EDGE_SECONDS)
        end = edge_time + EDGE_SECONDS
        return self._overlapping_windows(start, end, windows)

    def _field(self, item: object, name: str, fallback: float = 0.0) -> float:
        if item is None:
            return fallback
        return self._score(getattr(item, name, fallback), fallback)

    def _seconds(self, value: object, fallback: float = 0.0) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = fallback
        return round(max(0.0, numeric), 3)

    def _score(self, value: object, fallback: float = 0.0) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = fallback
        return round(max(0.0, min(1.0, numeric)), 3)

    def _avg(self, values: Any) -> float:
        clean = [self._score(value) for value in values]
        if not clean:
            return 0.0
        return self._score(sum(clean) / len(clean))

    def _max(self, values: Any) -> float:
        return self._score(max((self._score(value) for value in values), default=0.0))

    def _overlap_seconds(self, start_a: float, end_a: float, start_b: float, end_b: float) -> float:
        return max(0.0, min(end_a, end_b) - max(start_a, start_b))

    def _dedupe(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            text = str(value or "")
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
            if len(result) >= 30:
                break
        return result

    def _log(self, report: UniversalContextAuditReport) -> None:
        print(
            "[UNIVERSAL-CONTEXT-AUDIT] "
            f"segments={report.total_segments} "
            f"setup={report.keep_as_setup} "
            f"payoff={report.keep_as_payoff} "
            f"chain={report.keep_context_chain} "
            f"private_block={report.private_menu_block_candidate} "
            f"boring_bridge={report.boring_bridge_candidate} "
            f"boundary={report.boundary_protect} "
            f"edge_trim={report.edge_trim_candidate} "
            f"review={report.needs_human_review} "
            f"avg_conflict={report.avg_context_conflict_score}"
        )
