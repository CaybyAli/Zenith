from __future__ import annotations

from typing import Any

from models.universal_moment_debug_report import (
    UniversalMomentDebugReport,
    UniversalMomentSegmentDebug,
)
from models.universal_moment_soft_decision import (
    ENGINE,
    UniversalMomentSegmentDecision,
    UniversalMomentSoftDecisionReport,
)


FIRST_CONTEXT_PROTECTION_SECONDS = 30.0
PROTECTED_SEGMENT_ROLES = {"hook", "peak", "payoff"}


class UniversalMomentSoftDecisionBuilder:
    engine = ENGINE

    def build(
        self,
        *,
        job_id: str,
        debug_report=None,
    ) -> UniversalMomentSoftDecisionReport:
        parsed_report = self._debug_report(debug_report, job_id=job_id)
        decisions = [self._build_segment_decision(segment) for segment in parsed_report.segments]
        report = UniversalMomentSoftDecisionReport(
            job_id=str(job_id or parsed_report.job_id or ""),
            engine=self.engine,
            decisions=decisions,
        )
        self._log(report)
        return report

    def _build_segment_decision(
        self,
        segment: UniversalMomentSegmentDebug,
    ) -> UniversalMomentSegmentDecision:
        peak = self._score(segment.avg_peak_score)
        tension = self._score(segment.avg_tension_score)
        post_reaction = self._score(segment.avg_post_reaction_score)
        keep_score = self._score(segment.avg_keep_score)
        remove_score = self._score(segment.avg_remove_score)
        private_score = self._score(segment.avg_private_talk_score)
        boring_score = self._score(segment.avg_boring_score)
        menu_wait_score = self._score(getattr(segment, "avg_menu_wait_score", 0.0))
        speech_score = self._score(getattr(segment, "avg_speech_score", 0.0))
        cut_risk_score = self._score(segment.avg_cut_risk_score)
        raw_cut_risk_score = self._score(getattr(segment, "raw_cut_risk_score", 0.0))
        zoom_risk_score = self._score(segment.avg_zoom_risk_score)

        has_keep_signal = bool(segment.has_keep_signal)
        has_remove_signal = bool(segment.has_remove_signal)
        has_private_menu_risk = bool(segment.has_private_menu_risk)
        has_cut_risk = bool(segment.has_cut_risk)
        has_zoom_risk = bool(segment.has_zoom_risk)
        has_pre_context_need = bool(segment.has_pre_context_need)
        has_post_context_need = bool(segment.has_post_context_need)

        action_confidence = self._score(max(peak, tension, post_reaction, keep_score * 0.92))
        context_confidence = self._score(
            max(
                0.72 if has_pre_context_need or has_post_context_need else 0.0,
                tension * 0.82,
                post_reaction * 0.78,
                peak * 0.55,
            )
        )
        private_confidence = self._score(
            max(
                private_score,
                menu_wait_score * 0.86 if has_private_menu_risk else 0.0,
                0.66 if has_private_menu_risk else 0.0,
            )
        )
        boring_confidence = self._score(max(boring_score, remove_score * 0.92))
        keep_confidence = self._score(
            max(
                keep_score,
                peak,
                tension * 0.96,
                post_reaction * 0.98,
                0.62 if has_keep_signal else 0.0,
                0.56 if has_pre_context_need or has_post_context_need else 0.0,
            )
            + (0.05 if has_keep_signal else 0.0)
            + (0.03 if has_pre_context_need else 0.0)
            + (0.03 if has_post_context_need else 0.0)
        )
        remove_confidence = self._score(
            max(
                remove_score,
                private_confidence,
                boring_confidence,
                0.62 if has_remove_signal else 0.0,
                0.66 if has_private_menu_risk else 0.0,
            )
        )

        source_verdict = str(segment.professional_verdict or "unknown")
        source_mixed = source_verdict == "mixed_conflict"
        conflict_score = self._conflict_score(
            keep_confidence=keep_confidence,
            remove_confidence=remove_confidence,
            source_mixed=source_mixed,
        )
        is_mixed_conflict = source_mixed or (
            keep_confidence >= 0.40
            and remove_confidence >= 0.40
            and conflict_score >= 0.45
        )

        private_or_boring = max(private_confidence, boring_confidence)
        risk_confidence = self._score(
            max(
                cut_risk_score,
                raw_cut_risk_score,
                zoom_risk_score,
                0.76 if has_cut_risk else 0.0,
                0.72 if has_zoom_risk else 0.0,
            )
        )
        risk_private_combo = (
            risk_confidence >= 0.55
            and (remove_confidence >= 0.45 or private_confidence >= 0.55)
        )
        trim_confidence = self._score(
            (min(keep_confidence, remove_confidence) * 0.70)
            + (private_or_boring * 0.18)
            + (action_confidence * 0.12)
            + (0.10 if is_mixed_conflict else 0.0)
        )
        review_confidence = self._score(
            max(
                conflict_score,
                0.84 if risk_private_combo else 0.0,
                risk_confidence * 0.78 if risk_confidence >= 0.55 else 0.0,
                0.68 if source_verdict.startswith("review_") else 0.0,
            )
        )

        clear_keep_signal = max(peak, tension, post_reaction) >= 0.55
        safe_keep = (
            keep_confidence >= 0.65
            and remove_confidence < 0.35
            and conflict_score < 0.30
        )
        keep_dominant = (
            keep_confidence >= remove_confidence + 0.20
            and clear_keep_signal
        )
        remove_dominant = (
            remove_confidence >= keep_confidence + 0.25
            and (boring_score >= 0.70 or private_score >= 0.70)
            and peak < 0.35
            and tension < 0.35
        )
        trim_edges_candidate = (
            keep_confidence >= 0.40
            and remove_confidence >= 0.40
            and private_or_boring >= 0.50
            and action_confidence >= 0.30
            and (is_mixed_conflict or has_keep_signal)
        )
        needs_human_review = (
            conflict_score >= 0.45
            or risk_private_combo
            or (
                review_confidence >= 0.68
                and not safe_keep
                and not keep_dominant
                and not remove_dominant
                and not trim_edges_candidate
            )
        )

        soft_decision = "unknown"
        if safe_keep:
            soft_decision = "safe_keep"
        elif risk_private_combo:
            soft_decision = "needs_human_review"
        elif keep_dominant:
            soft_decision = "keep_dominant"
        elif remove_dominant:
            soft_decision = "remove_dominant"
        elif trim_edges_candidate:
            soft_decision = "trim_edges_candidate"
        elif needs_human_review or is_mixed_conflict:
            soft_decision = "needs_human_review"
        elif has_keep_signal and keep_confidence >= 0.50:
            soft_decision = "keep_dominant"
        elif has_remove_signal and remove_confidence >= 0.60:
            soft_decision = "remove_dominant"

        reasons: list[str] = []
        warnings: list[str] = []
        if clear_keep_signal:
            reasons.append("KEEP: strong peak/tension/post-reaction signal")
        elif has_keep_signal:
            reasons.append("KEEP: keep/context signal present")
        if remove_confidence >= 0.60 or has_remove_signal or has_private_menu_risk:
            reasons.append("REMOVE-SIGNAL: private/menu/boring dominates")
        if trim_edges_candidate:
            reasons.append("TRIM-CANDIDATE: mixed content, likely bad edges")
        if conflict_score >= 0.45 or is_mixed_conflict:
            reasons.append("REVIEW: keep and remove signals conflict")
        if risk_private_combo:
            reasons.append("REVIEW: cut/zoom risk overlaps remove/private signal")
        if risk_confidence >= 0.55 and not risk_private_combo:
            reasons.append("REVIEW: boundary risk present")

        first_30s = segment.start_time < FIRST_CONTEXT_PROTECTION_SECONDS
        protected_role = str(segment.segment_role or "").lower() in PROTECTED_SEGMENT_ROLES

        if first_30s:
            reasons.append("SAFETY: first 30s context protection")
            warnings.append("first_30s_context_protection")
            if soft_decision == "remove_dominant":
                soft_decision = "keep_dominant" if keep_confidence >= 0.55 and clear_keep_signal else "needs_human_review"

        if protected_role:
            reasons.append("SAFETY: protected segment role")
            warnings.append("protected_segment_role")
            if remove_confidence >= 0.55:
                soft_decision = (
                    "trim_edges_candidate"
                    if keep_confidence >= 0.40 and action_confidence >= 0.30
                    else "needs_human_review"
                )

        if soft_decision == "trim_edges_candidate" and "TRIM-CANDIDATE: mixed content, likely bad edges" not in reasons:
            reasons.append("TRIM-CANDIDATE: mixed content, likely bad edges")
        if soft_decision == "needs_human_review" and "REVIEW: keep and remove signals conflict" not in reasons and not risk_private_combo:
            reasons.append("REVIEW: no clear automatic soft decision")
        if soft_decision == "remove_dominant":
            warnings.append("QA6-X marker only; no automatic remove executed")
        if not reasons:
            reasons.append("INFO: no dominant universal moment signal")

        should_not_auto_remove = (
            soft_decision != "remove_dominant"
            or first_30s
            or protected_role
            or action_confidence >= 0.55
            or has_pre_context_need
            or has_post_context_need
            or has_cut_risk
            or has_zoom_risk
        )

        return UniversalMomentSegmentDecision(
            segment_id=segment.segment_id,
            start_time=segment.start_time,
            end_time=segment.end_time,
            duration_seconds=segment.duration_seconds,
            segment_role=segment.segment_role,
            keep_confidence=keep_confidence,
            remove_confidence=remove_confidence,
            trim_confidence=trim_confidence,
            review_confidence=review_confidence,
            conflict_score=conflict_score,
            private_confidence=private_confidence,
            boring_confidence=boring_confidence,
            action_confidence=action_confidence,
            speech_confidence=speech_score,
            context_confidence=context_confidence,
            soft_decision=soft_decision,
            is_mixed_conflict=is_mixed_conflict,
            should_not_auto_remove=should_not_auto_remove,
            can_trim_edges_later=soft_decision == "trim_edges_candidate",
            needs_human_review=soft_decision == "needs_human_review",
            protect_pre_context=has_pre_context_need or first_30s,
            protect_post_context=has_post_context_need,
            reasons=self._dedupe(reasons),
            warnings=self._dedupe(warnings),
            source_verdict=source_verdict,
            source_diagnosis=list(segment.diagnosis or []),
        )

    def _debug_report(self, report: Any, *, job_id: str) -> UniversalMomentDebugReport:
        if isinstance(report, UniversalMomentDebugReport):
            return report
        if isinstance(report, dict):
            return UniversalMomentDebugReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return UniversalMomentDebugReport.from_dict(report.to_dict())
        return UniversalMomentDebugReport(job_id=str(job_id or ""))

    def _conflict_score(
        self,
        *,
        keep_confidence: float,
        remove_confidence: float,
        source_mixed: bool,
    ) -> float:
        weaker = min(keep_confidence, remove_confidence)
        if weaker <= 0.15:
            return 0.0
        simultaneous = max(0.0, (weaker - 0.15) / 0.85)
        balance = 1.0 - abs(keep_confidence - remove_confidence)
        return self._score(
            (simultaneous * 0.72)
            + (balance * 0.18)
            + (0.10 if source_mixed else 0.0)
        )

    def _score(self, value: object, fallback: float = 0.0) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = fallback
        return round(max(0.0, min(1.0, numeric)), 3)

    def _dedupe(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            text = str(value or "")
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

    def _log(self, report: UniversalMomentSoftDecisionReport) -> None:
        print(
            "[UNIVERSAL-SOFT-DECISION] "
            f"segments={report.total_segments} "
            f"safe_keep={report.safe_keep} "
            f"keep={report.keep_dominant} "
            f"trim={report.trim_edges_candidate} "
            f"remove={report.remove_dominant} "
            f"review={report.needs_human_review} "
            f"avg_conflict={report.avg_conflict_score}"
        )
