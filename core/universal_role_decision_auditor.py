from __future__ import annotations

from typing import Any

from models.universal_moment_debug_report import (
    UniversalMomentDebugReport,
    UniversalMomentSegmentDebug,
)
from models.universal_moment_soft_decision import (
    UniversalMomentSegmentDecision,
    UniversalMomentSoftDecisionReport,
)
from models.universal_role_decision_audit import (
    ENGINE,
    UniversalRoleDecisionAuditReport,
    UniversalRoleDecisionSegmentAudit,
)


FIRST_30S = 30.0
PROTECTED_ROLES = {"hook", "peak", "payoff"}


class UniversalRoleDecisionAuditor:
    engine = ENGINE

    def build(
        self,
        *,
        job_id: str,
        debug_report=None,
        soft_decision_report=None,
    ) -> UniversalRoleDecisionAuditReport:
        parsed_debug = self._debug_report(debug_report, job_id=job_id)
        parsed_soft = self._soft_decision_report(soft_decision_report, job_id=job_id)

        debug_by_id = {
            segment.segment_id: segment
            for segment in parsed_debug.segments
            if segment.segment_id
        }
        decisions_by_id = {
            decision.segment_id: decision
            for decision in parsed_soft.decisions
            if decision.segment_id
        }

        audits: list[UniversalRoleDecisionSegmentAudit] = []
        used_decisions: set[str] = set()

        for segment in parsed_debug.segments:
            decision = decisions_by_id.get(segment.segment_id)
            if decision is None:
                decision = self._find_decision_by_time(parsed_soft.decisions, segment)
            if decision is not None and decision.segment_id:
                used_decisions.add(decision.segment_id)
            audits.append(self._build_segment_audit(segment=segment, decision=decision))

        for decision in parsed_soft.decisions:
            if decision.segment_id in used_decisions or decision.segment_id in debug_by_id:
                continue
            audits.append(self._build_segment_audit(segment=None, decision=decision))

        report = UniversalRoleDecisionAuditReport(
            job_id=str(job_id or parsed_debug.job_id or parsed_soft.job_id or ""),
            engine=self.engine,
            segments=audits,
        )
        self._log(report)
        return report

    def _build_segment_audit(
        self,
        *,
        segment: UniversalMomentSegmentDebug | None,
        decision: UniversalMomentSegmentDecision | None,
    ) -> UniversalRoleDecisionSegmentAudit:
        segment_id = str(
            getattr(segment, "segment_id", None)
            or getattr(decision, "segment_id", None)
            or ""
        )
        role = str(
            getattr(segment, "segment_role", None)
            or getattr(decision, "segment_role", None)
            or "unknown"
        )
        start_time = self._scoreless(
            getattr(segment, "start_time", None)
            if segment is not None
            else getattr(decision, "start_time", 0.0)
        )
        end_time = self._scoreless(
            getattr(segment, "end_time", None)
            if segment is not None
            else getattr(decision, "end_time", start_time)
        )
        if end_time <= start_time:
            end_time = round(start_time + 0.001, 3)

        soft_decision = str(getattr(decision, "soft_decision", "unknown") or "unknown")
        professional_verdict = str(
            getattr(segment, "professional_verdict", None)
            or getattr(decision, "source_verdict", None)
            or "unknown"
        )
        protected_role = role.lower() in PROTECTED_ROLES
        first_30s = start_time < FIRST_30S

        scores = {
            "keep_confidence": self._score(getattr(decision, "keep_confidence", 0.0)),
            "remove_confidence": self._score(getattr(decision, "remove_confidence", 0.0)),
            "trim_confidence": self._score(getattr(decision, "trim_confidence", 0.0)),
            "review_confidence": self._score(getattr(decision, "review_confidence", 0.0)),
            "conflict_score": self._score(getattr(decision, "conflict_score", 0.0)),
            "avg_peak_score": self._score(getattr(segment, "avg_peak_score", 0.0)),
            "avg_tension_score": self._score(getattr(segment, "avg_tension_score", 0.0)),
            "avg_private_talk_score": self._score(
                getattr(segment, "avg_private_talk_score", 0.0)
            ),
            "avg_boring_score": self._score(getattr(segment, "avg_boring_score", 0.0)),
            "avg_cut_risk_score": self._score(getattr(segment, "avg_cut_risk_score", 0.0)),
            "avg_zoom_risk_score": self._score(getattr(segment, "avg_zoom_risk_score", 0.0)),
        }

        alignment, suggestion, reason, warnings, notes = self._classify(
            role=role,
            soft_decision=soft_decision,
            professional_verdict=professional_verdict,
            is_protected_role=protected_role,
            is_first_30s=first_30s,
            **scores,
        )

        return UniversalRoleDecisionSegmentAudit(
            segment_id=segment_id,
            segment_role=role,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=end_time - start_time,
            soft_decision=soft_decision,
            professional_verdict=professional_verdict,
            is_protected_role=protected_role,
            is_first_30s=first_30s,
            role_decision_alignment=alignment,
            suggested_soft_decision=suggestion,
            suggested_reason=reason,
            warnings=warnings,
            notes=notes,
            **scores,
        )

    def _classify(
        self,
        *,
        role: str,
        soft_decision: str,
        professional_verdict: str,
        is_protected_role: bool,
        is_first_30s: bool,
        keep_confidence: float,
        remove_confidence: float,
        trim_confidence: float,
        review_confidence: float,
        conflict_score: float,
        avg_peak_score: float,
        avg_tension_score: float,
        avg_private_talk_score: float,
        avg_boring_score: float,
        avg_cut_risk_score: float,
        avg_zoom_risk_score: float,
    ) -> tuple[str, str, str, list[str], list[str]]:
        del trim_confidence, review_confidence
        role_name = str(role or "unknown").lower()
        warnings: list[str] = []
        notes: list[str] = []

        if is_first_30s:
            notes.append("first_30s_context_protection_active")
        if avg_cut_risk_score >= 0.55:
            notes.append("cut_risk_signal_present")
        if avg_zoom_risk_score >= 0.55:
            notes.append("zoom_risk_signal_present")

        if is_protected_role and soft_decision == "trim_edges_candidate":
            warnings.append("protected_role_marked_as_trim_candidate")
            suggested = (
                "needs_human_review"
                if conflict_score >= 0.45 or avg_cut_risk_score >= 0.45 or avg_zoom_risk_score >= 0.45
                else "keep_protected"
            )
            return (
                "protected_trim_conflict",
                suggested,
                "Protected role was marked as trim candidate; do not auto-trim without stronger evidence.",
                warnings,
                notes,
            )

        if is_protected_role and soft_decision == "remove_dominant":
            warnings.append("protected_role_marked_as_remove_dominant")
            return (
                "remove_blocked_by_role",
                "needs_human_review",
                "Protected role was marked remove-dominant; keep protected or review instead of removing.",
                warnings,
                notes,
            )

        if (
            soft_decision == "needs_human_review"
            and role_name not in PROTECTED_ROLES
            and remove_confidence >= 0.45
            and keep_confidence >= 0.45
            and (avg_private_talk_score >= 0.55 or avg_boring_score >= 0.55)
            and avg_peak_score < 0.55
            and avg_tension_score < 0.55
        ):
            notes.append("review_has_private_or_boring_edge_signal")
            return (
                "review_maybe_trim",
                "consider_trim_edges",
                "Human-review segment may be edge-trimmable because remove/private/boring signals are present without strong peak/tension.",
                warnings,
                notes,
            )

        if (
            soft_decision == "safe_keep"
            and keep_confidence >= 0.60
            and remove_confidence < 0.45
        ):
            return (
                "safe_keep_correct",
                "keep_current",
                "Safe keep is consistent with strong keep confidence and weak remove confidence.",
                warnings,
                notes,
            )

        if self._is_aligned(
            role=role_name,
            soft_decision=soft_decision,
            professional_verdict=professional_verdict,
            is_protected_role=is_protected_role,
            keep_confidence=keep_confidence,
            remove_confidence=remove_confidence,
            conflict_score=conflict_score,
            avg_peak_score=avg_peak_score,
            avg_tension_score=avg_tension_score,
            avg_private_talk_score=avg_private_talk_score,
            avg_boring_score=avg_boring_score,
            avg_cut_risk_score=avg_cut_risk_score,
            avg_zoom_risk_score=avg_zoom_risk_score,
        ):
            return (
                "aligned",
                "keep_current",
                "Role and soft decision do not conflict under current QA6-Z audit rules.",
                warnings,
                notes,
            )

        return (
            "unclear",
            "unknown",
            "Signals are insufficient or contradictory; keep the current conservative decision and inspect manually.",
            warnings,
            notes,
        )

    def _is_aligned(
        self,
        *,
        role: str,
        soft_decision: str,
        professional_verdict: str,
        is_protected_role: bool,
        keep_confidence: float,
        remove_confidence: float,
        conflict_score: float,
        avg_peak_score: float,
        avg_tension_score: float,
        avg_private_talk_score: float,
        avg_boring_score: float,
        avg_cut_risk_score: float,
        avg_zoom_risk_score: float,
    ) -> bool:
        if soft_decision == "unknown":
            return False
        if is_protected_role and soft_decision in {"safe_keep", "keep_dominant", "needs_human_review"}:
            return True
        if soft_decision == "trim_edges_candidate":
            return (
                role not in PROTECTED_ROLES
                and remove_confidence >= 0.45
                and keep_confidence >= 0.45
                and max(avg_private_talk_score, avg_boring_score) >= 0.45
                and avg_peak_score < 0.60
                and avg_tension_score < 0.60
            )
        if soft_decision == "needs_human_review":
            return (
                conflict_score >= 0.55
                or avg_cut_risk_score >= 0.45
                or avg_zoom_risk_score >= 0.45
                or professional_verdict.startswith("review_")
                or professional_verdict == "mixed_conflict"
            )
        if soft_decision == "keep_dominant":
            return keep_confidence >= remove_confidence and max(avg_peak_score, avg_tension_score) >= 0.45
        if soft_decision == "remove_dominant":
            return (
                not is_protected_role
                and remove_confidence >= keep_confidence
                and max(avg_private_talk_score, avg_boring_score) >= 0.55
                and avg_peak_score < 0.55
                and avg_tension_score < 0.55
            )
        if soft_decision == "safe_keep":
            return keep_confidence >= remove_confidence and remove_confidence < 0.50
        return False

    def _debug_report(self, report: Any, *, job_id: str) -> UniversalMomentDebugReport:
        if isinstance(report, UniversalMomentDebugReport):
            return report
        if isinstance(report, dict):
            return UniversalMomentDebugReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return UniversalMomentDebugReport.from_dict(report.to_dict())
        return UniversalMomentDebugReport(job_id=str(job_id or ""))

    def _soft_decision_report(
        self,
        report: Any,
        *,
        job_id: str,
    ) -> UniversalMomentSoftDecisionReport:
        if isinstance(report, UniversalMomentSoftDecisionReport):
            return report
        if isinstance(report, dict):
            return UniversalMomentSoftDecisionReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return UniversalMomentSoftDecisionReport.from_dict(report.to_dict())
        return UniversalMomentSoftDecisionReport(job_id=str(job_id or ""))

    def _find_decision_by_time(
        self,
        decisions: list[UniversalMomentSegmentDecision],
        segment: UniversalMomentSegmentDebug,
    ) -> UniversalMomentSegmentDecision | None:
        best: UniversalMomentSegmentDecision | None = None
        best_overlap = 0.0
        for decision in decisions:
            overlap = self._overlap_seconds(
                segment.start_time,
                segment.end_time,
                decision.start_time,
                decision.end_time,
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best = decision
        return best if best_overlap > 0.0 else None

    def _score(self, value: object, fallback: float = 0.0) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = fallback
        return round(max(0.0, min(1.0, numeric)), 3)

    def _scoreless(self, value: object, fallback: float = 0.0) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = fallback
        return round(max(0.0, numeric), 3)

    def _overlap_seconds(self, start_a: float, end_a: float, start_b: float, end_b: float) -> float:
        return max(0.0, min(end_a, end_b) - max(start_a, start_b))

    def _log(self, report: UniversalRoleDecisionAuditReport) -> None:
        print(
            "[UNIVERSAL-ROLE-AUDIT] "
            f"segments={report.total_segments} "
            f"protected_trim_conflicts={report.protected_trim_conflicts} "
            f"review_maybe_trim={report.review_maybe_trim} "
            f"safe_keep_correct={report.safe_keep_correct} "
            f"aligned={report.aligned} "
            f"unclear={report.unclear}"
        )
