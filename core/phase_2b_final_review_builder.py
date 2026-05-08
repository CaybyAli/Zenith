from __future__ import annotations

from typing import Any

from models.phase_2b_final_review import (
    ENGINE,
    Phase2BFinalReviewReport,
    Phase2BSegmentReview,
)
from models.universal_boundary_evidence import (
    UniversalBoundaryEvidence,
    UniversalBoundaryEvidenceReport,
)
from models.universal_context_audit import (
    UniversalContextAuditReport,
    UniversalSegmentContextAudit,
)
from models.universal_moment_debug_report import (
    UniversalMomentDebugReport,
    UniversalMomentSegmentDebug,
)
from models.universal_moment_soft_decision import (
    UniversalMomentSegmentDecision,
    UniversalMomentSoftDecisionReport,
)
from models.universal_role_decision_audit import (
    UniversalRoleDecisionAuditReport,
    UniversalRoleDecisionSegmentAudit,
)


PROTECTED_ROLES = {"hook", "peak", "payoff"}
BOUNDARY_RISK_TYPES = {"speech_cut_risk", "action_cut_risk", "zoom_cut_risk"}
KEEP_CONTEXT_DECISIONS = {"keep_as_payoff", "keep_as_setup", "keep_context_chain"}


class Phase2BFinalReviewBuilder:
    engine = ENGINE

    def build(
        self,
        *,
        job_id: str,
        debug_report=None,
        soft_decision_report=None,
        role_decision_audit_report=None,
        context_audit_report=None,
        boundary_evidence_report=None,
    ) -> Phase2BFinalReviewReport:
        parsed_debug = self._debug_report(debug_report, job_id=job_id)
        parsed_soft = self._soft_report(soft_decision_report, job_id=job_id)
        parsed_role = self._role_report(role_decision_audit_report, job_id=job_id)
        parsed_context = self._context_report(context_audit_report, job_id=job_id)
        parsed_boundary_evidence = self._boundary_evidence_report(
            boundary_evidence_report,
            job_id=job_id,
        )

        debug_by_id = {item.segment_id: item for item in parsed_debug.segments if item.segment_id}
        soft_by_id = {item.segment_id: item for item in parsed_soft.decisions if item.segment_id}
        role_by_id = {item.segment_id: item for item in parsed_role.segments if item.segment_id}
        context_by_id = {item.segment_id: item for item in parsed_context.segments if item.segment_id}
        boundary_evidence_by_id = self._boundary_evidence_by_segment(parsed_boundary_evidence)

        segment_ids = self._ordered_segment_ids(
            parsed_debug=parsed_debug,
            parsed_soft=parsed_soft,
            parsed_role=parsed_role,
            parsed_context=parsed_context,
        )

        reviews: list[Phase2BSegmentReview] = []
        for index, segment_id in enumerate(segment_ids, start=1):
            debug = debug_by_id.get(segment_id)
            soft = soft_by_id.get(segment_id) or self._matching_soft(debug, parsed_soft.decisions)
            role = role_by_id.get(segment_id) or self._matching_role(debug, parsed_role.segments)
            context = context_by_id.get(segment_id) or self._matching_context(debug, parsed_context.segments)
            reviews.append(
                self._build_segment_review(
                    index=index,
                    segment_id=segment_id,
                    debug=debug,
                    soft=soft,
                    role=role,
                    context=context,
                    boundary_evidence=boundary_evidence_by_id.get(segment_id, []),
                )
            )

        report = Phase2BFinalReviewReport(
            job_id=str(
                job_id
                or parsed_debug.job_id
                or parsed_soft.job_id
                or parsed_context.job_id
                or parsed_boundary_evidence.job_id
                or ""
            ),
            engine=self.engine,
            segments=reviews,
        )
        self._log(report)
        return report

    def _build_segment_review(
        self,
        *,
        index: int,
        segment_id: str,
        debug: UniversalMomentSegmentDebug | None,
        soft: UniversalMomentSegmentDecision | None,
        role: UniversalRoleDecisionSegmentAudit | None,
        context: UniversalSegmentContextAudit | None,
        boundary_evidence: list[UniversalBoundaryEvidence],
    ) -> Phase2BSegmentReview:
        start = self._first_number("start_time", debug, soft, role, context)
        end = self._first_number("end_time", debug, soft, role, context, fallback=start + 0.001)
        segment_role = self._first_text("segment_role", debug, soft, role, context, fallback="unknown")
        professional_verdict = self._first_text("professional_verdict", debug, role, fallback="unknown")
        soft_decision = str(getattr(soft, "soft_decision", "unknown") or "unknown")
        context_decision = str(getattr(context, "context_decision", "unknown") or "unknown")

        keep_confidence = self._score(
            max(
                self._field(soft, "keep_confidence"),
                self._field(debug, "avg_keep_score"),
                self._field(debug, "avg_peak_score"),
                self._field(debug, "avg_tension_score"),
                self._field(debug, "avg_post_reaction_score"),
            )
        )
        remove_confidence = self._score(
            max(
                self._field(soft, "remove_confidence"),
                self._field(debug, "avg_remove_score"),
                self._field(debug, "avg_private_talk_score"),
                self._field(debug, "avg_boring_score"),
                self._field(debug, "avg_menu_wait_score"),
            )
        )
        conflict_score = self._score(self._field(soft, "conflict_score"))
        context_conflict_score = self._score(self._field(context, "context_conflict_score"))
        previous_boundary_type = str(getattr(context, "previous_boundary_type", "clean") or "clean")
        next_boundary_type = str(getattr(context, "next_boundary_type", "clean") or "clean")
        protect_previous = bool(getattr(context, "should_protect_previous_boundary", False))
        protect_next = bool(getattr(context, "should_protect_next_boundary", False))
        raw_boundary_risk = (
            (previous_boundary_type in BOUNDARY_RISK_TYPES and protect_previous)
            or (next_boundary_type in BOUNDARY_RISK_TYPES and protect_next)
        )
        boundary_risk = self._boundary_risk_from_evidence(
            raw_boundary_risk=raw_boundary_risk,
            boundary_evidence=boundary_evidence,
        )
        protected_role = bool(getattr(role, "is_protected_role", False)) or str(segment_role).lower() in PROTECTED_ROLES
        first_30s = bool(getattr(role, "is_first_30s", False)) or start < 30.0
        possible_edge_trim = (
            context_decision == "edge_trim_candidate"
            or str(getattr(role, "suggested_soft_decision", "unknown") or "unknown") == "consider_trim_edges"
        ) and not protected_role and not first_30s

        status = self._status(
            soft_decision=soft_decision,
            context_decision=context_decision,
            keep_confidence=keep_confidence,
            remove_confidence=remove_confidence,
            conflict_score=conflict_score,
            context_conflict_score=context_conflict_score,
            boundary_risk=boundary_risk,
            possible_edge_trim=possible_edge_trim,
            soft=soft,
            role=role,
        )
        priority, priority_reason = self._priority(
            status=status,
            debug=debug,
            soft=soft,
            role=role,
            context=context,
            keep_confidence=keep_confidence,
            remove_confidence=remove_confidence,
            conflict_score=conflict_score,
            context_conflict_score=context_conflict_score,
            boundary_risk=boundary_risk,
            raw_boundary_risk=raw_boundary_risk,
            boundary_evidence=boundary_evidence,
            possible_edge_trim=possible_edge_trim,
            previous_boundary_type=previous_boundary_type,
            next_boundary_type=next_boundary_type,
        )

        return Phase2BSegmentReview(
            segment_id=segment_id,
            index=index,
            segment_role=segment_role,
            start_time=start,
            end_time=end,
            duration_seconds=max(0.001, end - start),
            soft_decision=soft_decision,
            context_decision=context_decision,
            professional_verdict=professional_verdict,
            final_review_status=status,
            keep_confidence=keep_confidence,
            remove_confidence=remove_confidence,
            conflict_score=conflict_score,
            context_conflict_score=context_conflict_score,
            previous_boundary_type=previous_boundary_type,
            next_boundary_type=next_boundary_type,
            protect_previous_boundary=protect_previous,
            protect_next_boundary=protect_next,
            human_review_priority=priority,
            human_review_reason=priority_reason,
            key_reasons=self._key_reasons(
                debug=debug,
                soft=soft,
                role=role,
                context=context,
                boundary_evidence=boundary_evidence,
            ),
            warnings=self._warnings(
                soft=soft,
                role=role,
                context=context,
                boundary_evidence=boundary_evidence,
            ),
        )

    def _status(
        self,
        *,
        soft_decision: str,
        context_decision: str,
        keep_confidence: float,
        remove_confidence: float,
        conflict_score: float,
        context_conflict_score: float,
        boundary_risk: bool,
        possible_edge_trim: bool,
        soft: UniversalMomentSegmentDecision | None,
        role: UniversalRoleDecisionSegmentAudit | None,
    ) -> str:
        keep_context = context_decision in KEEP_CONTEXT_DECISIONS
        strong_keep_signal = soft_decision in {"safe_keep", "keep_dominant"} or (
            keep_confidence >= 0.65 and keep_context
        )
        review_signal = (
            soft_decision == "needs_human_review"
            or context_decision == "needs_human_review"
            or conflict_score >= 0.55
            or context_conflict_score >= 0.55
            or bool(getattr(soft, "is_mixed_conflict", False))
            or str(getattr(role, "role_decision_alignment", "aligned") or "aligned") in {"unclear", "protected_trim_conflict"}
        )
        if possible_edge_trim:
            return "possible_edge_trim_later"
        if strong_keep_signal and boundary_risk:
            return "keep_with_boundary_warning"
        if strong_keep_signal and keep_context and not boundary_risk and remove_confidence < 0.45:
            return "strong_keep"
        if review_signal:
            return "review_needed"
        if not boundary_risk and conflict_score < 0.35 and context_conflict_score < 0.45 and remove_confidence < 0.45:
            return "safe"
        return "review_needed"

    def _priority(
        self,
        *,
        status: str,
        debug: UniversalMomentSegmentDebug | None,
        soft: UniversalMomentSegmentDecision | None,
        role: UniversalRoleDecisionSegmentAudit | None,
        context: UniversalSegmentContextAudit | None,
        keep_confidence: float,
        remove_confidence: float,
        conflict_score: float,
        context_conflict_score: float,
        boundary_risk: bool,
        raw_boundary_risk: bool,
        boundary_evidence: list[UniversalBoundaryEvidence],
        possible_edge_trim: bool,
        previous_boundary_type: str,
        next_boundary_type: str,
    ) -> tuple[str, str]:
        conflict = max(conflict_score, context_conflict_score)
        speech_or_action_boundary = any(
            boundary in {"speech_cut_risk", "action_cut_risk"}
            for boundary in (previous_boundary_type, next_boundary_type)
        )
        protected_weak = "protected_role_without_strong_payoff_signal" in set(getattr(context, "warnings", []) or [])
        confirmed_cut_conflict = bool(getattr(debug, "confirmed_cut_risk", False) or getattr(debug, "has_cut_risk", False)) and conflict >= 0.45
        if confirmed_cut_conflict:
            return "high", "Confirmed cut risk overlaps keep/remove or context conflict."
        if any(
            item.speech_boundary_classification == "likely_speech_cut"
            for item in boundary_evidence
        ):
            if conflict >= 0.45 or keep_confidence >= 0.70:
                return "high", "Likely speech cut overlaps conflict or strong keep signal."
            return "medium", "Boundary transcript evidence indicates likely speech cut; manual check recommended."
        evidence_priority, evidence_reason = self._boundary_evidence_priority(boundary_evidence)
        if evidence_priority == "high":
            return "high", evidence_reason
        if evidence_priority == "medium":
            return "medium", evidence_reason
        if raw_boundary_risk and evidence_priority == "low":
            return "low", evidence_reason
        if boundary_risk and speech_or_action_boundary:
            return "high", "Speech/action boundary risk needs visual or transcript verification."
        if protected_weak:
            return "high", "Protected role lacks strong payoff signal; verify before trusting role."
        if possible_edge_trim and conflict >= 0.35:
            return "high", "Possible edge trim still has conflict and needs manual review."

        zoom_boundary = any(boundary == "zoom_cut_risk" for boundary in (previous_boundary_type, next_boundary_type))
        unclear = (
            str(getattr(role, "role_decision_alignment", "aligned") or "aligned") == "unclear"
            or str(getattr(context, "context_decision", "unknown") or "unknown") in {"unknown", "needs_human_review"}
        )
        private_menu_conflict = (
            remove_confidence >= 0.45
            and keep_confidence >= 0.45
            and (
                self._field(debug, "avg_private_talk_score") >= 0.50
                or self._field(debug, "avg_menu_wait_score") >= 0.50
                or self._field(debug, "avg_boring_score") >= 0.50
            )
        )
        if zoom_boundary or bool(getattr(debug, "has_zoom_risk", False)):
            return "medium", "Zoom boundary/risk should be checked against framing."
        if private_menu_conflict:
            return "medium", "Private/menu/remove signal coexists with keep signal."
        if unclear:
            return "medium", "Context or role alignment remains unclear."
        if status in {"strong_keep", "safe"}:
            return "none", "No human review needed from Phase 2.B diagnostics."
        return "low", "Safe-looking segment, but review can still confirm pacing."

    def _boundary_risk_from_evidence(
        self,
        *,
        raw_boundary_risk: bool,
        boundary_evidence: list[UniversalBoundaryEvidence],
    ) -> bool:
        if not boundary_evidence:
            return raw_boundary_risk
        if any(
            item.speech_boundary_classification in {"real_word_cut", "real_sentence_cut"}
            or item.boundary_type in {"action_cut_risk", "zoom_cut_risk"}
            or (
                item.priority == "real_high"
                and item.speech_boundary_classification
                not in {"audio_only_near_edge", "weak_speech_evidence", "probably_safe"}
            )
            for item in boundary_evidence
        ):
            return True
        if any(
            item.speech_boundary_classification in {"likely_speech_cut", "timestamp_uncertain"}
            or item.priority == "medium"
            for item in boundary_evidence
        ):
            return True
        if raw_boundary_risk and all(
            item.speech_boundary_classification in {
                "audio_only_near_edge",
                "weak_speech_evidence",
                "probably_safe",
            }
            or item.priority in {"false_positive", "low"}
            or item.boundary_type in {"likely_false_positive", "clean"}
            for item in boundary_evidence
        ):
            return False
        return raw_boundary_risk

    def _boundary_evidence_priority(
        self,
        boundary_evidence: list[UniversalBoundaryEvidence],
    ) -> tuple[str, str]:
        if not boundary_evidence:
            return "unknown", ""
        if any(
            item.speech_boundary_classification in {"real_word_cut", "real_sentence_cut"}
            for item in boundary_evidence
        ):
            types = ", ".join(
                sorted(
                    {
                        item.speech_boundary_classification
                        for item in boundary_evidence
                        if item.speech_boundary_classification in {"real_word_cut", "real_sentence_cut"}
                    }
                )
            )
            return "high", f"Boundary transcript evidence confirms high-priority edge risk: {types}."
        if any(item.boundary_type in {"action_cut_risk", "zoom_cut_risk"} for item in boundary_evidence):
            types = ", ".join(
                sorted(
                    {
                        item.boundary_type
                        for item in boundary_evidence
                        if item.boundary_type in {"action_cut_risk", "zoom_cut_risk"}
                    }
                )
            )
            return "high", f"Boundary evidence confirms high-priority visual edge risk: {types}."
        if any(item.speech_boundary_classification == "timestamp_uncertain" for item in boundary_evidence):
            return "medium", "Transcript boundary evidence uncertain; manual check recommended."
        if any(item.priority == "medium" for item in boundary_evidence):
            types = ", ".join(
                sorted(
                    {
                        item.speech_boundary_classification
                        if item.speech_boundary_classification != "unknown"
                        else item.boundary_type
                        for item in boundary_evidence
                        if item.priority == "medium"
                    }
                )
            )
            return "medium", f"Boundary evidence indicates medium-priority edge review: {types}."
        if any(item.speech_boundary_classification == "audio_only_near_edge" for item in boundary_evidence):
            return "low", "Boundary transcript evidence is audio-only near edge; spot-check if pacing looks suspicious."
        if any(item.speech_boundary_classification == "weak_speech_evidence" for item in boundary_evidence):
            return "low", "Boundary speech evidence is weak after calibration."
        if all(
            item.speech_boundary_classification in {"probably_safe", "weak_speech_evidence"}
            or item.priority in {"false_positive", "low"}
            or item.boundary_type in {"likely_false_positive", "clean"}
            for item in boundary_evidence
        ):
            return "low", "Boundary evidence downgrades the prior warning to clean or likely false positive."
        return "unknown", ""

    def _ordered_segment_ids(
        self,
        *,
        parsed_debug: UniversalMomentDebugReport,
        parsed_soft: UniversalMomentSoftDecisionReport,
        parsed_role: UniversalRoleDecisionAuditReport,
        parsed_context: UniversalContextAuditReport,
    ) -> list[str]:
        raw: list[tuple[float, float, str]] = []
        for collection in (
            parsed_debug.segments,
            parsed_soft.decisions,
            parsed_role.segments,
            parsed_context.segments,
        ):
            for item in collection:
                segment_id = str(getattr(item, "segment_id", "") or "")
                if not segment_id:
                    continue
                raw.append(
                    (
                        self._seconds(getattr(item, "start_time", 0.0)),
                        self._seconds(getattr(item, "end_time", 0.0)),
                        segment_id,
                    )
                )
        result: list[str] = []
        seen: set[str] = set()
        for _, _, segment_id in sorted(raw):
            if segment_id in seen:
                continue
            seen.add(segment_id)
            result.append(segment_id)
        return result

    def _key_reasons(
        self,
        *,
        debug: UniversalMomentSegmentDebug | None,
        soft: UniversalMomentSegmentDecision | None,
        role: UniversalRoleDecisionSegmentAudit | None,
        context: UniversalSegmentContextAudit | None,
        boundary_evidence: list[UniversalBoundaryEvidence],
    ) -> list[str]:
        values: list[str] = []
        values.extend(getattr(soft, "reasons", []) or [])
        values.extend(getattr(context, "reasons", []) or [])
        for evidence in boundary_evidence:
            values.extend(getattr(evidence, "reasons", []) or [])
        suggested_reason = str(getattr(role, "suggested_reason", "") or "")
        if suggested_reason:
            values.append(suggested_reason)
        professional_reason = str(getattr(debug, "professional_reason", "") or "")
        if professional_reason:
            values.append(professional_reason)
        return self._dedupe(values, limit=12)

    def _warnings(
        self,
        *,
        soft: UniversalMomentSegmentDecision | None,
        role: UniversalRoleDecisionSegmentAudit | None,
        context: UniversalSegmentContextAudit | None,
        boundary_evidence: list[UniversalBoundaryEvidence],
    ) -> list[str]:
        values: list[str] = []
        values.extend(getattr(soft, "warnings", []) or [])
        values.extend(getattr(role, "warnings", []) or [])
        values.extend(getattr(context, "warnings", []) or [])
        for evidence in boundary_evidence:
            boundary_type = str(getattr(evidence, "boundary_type", "") or "")
            speech_classification = str(
                getattr(evidence, "speech_boundary_classification", "") or ""
            )
            if speech_classification == "timestamp_uncertain":
                values.append("Boundary transcript evidence: timestamp uncertain")
            elif speech_classification == "audio_only_near_edge":
                values.append("Boundary transcript evidence: audio-only near edge")
            elif speech_classification == "real_word_cut":
                values.append("Boundary transcript evidence: likely real word cut")
            elif speech_classification == "real_sentence_cut":
                values.append("Boundary transcript evidence: likely real sentence cut")
            elif boundary_type == "real_speech_cut_risk":
                values.append("Boundary evidence: real speech cut risk")
            elif boundary_type == "likely_false_positive":
                values.append("Boundary evidence: likely false positive")
            elif boundary_type == "action_cut_risk":
                values.append("Boundary evidence: action near edge")
            elif boundary_type == "zoom_cut_risk":
                values.append("Boundary evidence: zoom near edge")
        return self._dedupe(values, limit=12)

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

    def _context_report(self, report: Any, *, job_id: str) -> UniversalContextAuditReport:
        if isinstance(report, UniversalContextAuditReport):
            return report
        if isinstance(report, dict):
            return UniversalContextAuditReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return UniversalContextAuditReport.from_dict(report.to_dict())
        return UniversalContextAuditReport(job_id=str(job_id or ""))

    def _boundary_evidence_report(self, report: Any, *, job_id: str) -> UniversalBoundaryEvidenceReport:
        if isinstance(report, UniversalBoundaryEvidenceReport):
            return report
        if isinstance(report, dict):
            return UniversalBoundaryEvidenceReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return UniversalBoundaryEvidenceReport.from_dict(report.to_dict())
        return UniversalBoundaryEvidenceReport(job_id=str(job_id or ""))

    def _boundary_evidence_by_segment(
        self,
        report: UniversalBoundaryEvidenceReport,
    ) -> dict[str, list[UniversalBoundaryEvidence]]:
        result: dict[str, list[UniversalBoundaryEvidence]] = {}
        for boundary in report.boundaries:
            for segment_id in (boundary.left_segment_id, boundary.right_segment_id):
                if not segment_id:
                    continue
                result.setdefault(segment_id, []).append(boundary)
        return result

    def _matching_soft(
        self,
        debug: UniversalMomentSegmentDebug | None,
        items: list[UniversalMomentSegmentDecision],
    ) -> UniversalMomentSegmentDecision | None:
        return self._find_by_time(debug, items)

    def _matching_role(
        self,
        debug: UniversalMomentSegmentDebug | None,
        items: list[UniversalRoleDecisionSegmentAudit],
    ) -> UniversalRoleDecisionSegmentAudit | None:
        return self._find_by_time(debug, items)

    def _matching_context(
        self,
        debug: UniversalMomentSegmentDebug | None,
        items: list[UniversalSegmentContextAudit],
    ) -> UniversalSegmentContextAudit | None:
        return self._find_by_time(debug, items)

    def _find_by_time(self, source: object | None, items: list[Any]) -> Any | None:
        if source is None:
            return None
        start = self._seconds(getattr(source, "start_time", 0.0))
        end = self._seconds(getattr(source, "end_time", 0.0))
        best = None
        best_overlap = 0.0
        for item in items:
            overlap = max(
                0.0,
                min(end, self._seconds(getattr(item, "end_time", 0.0)))
                - max(start, self._seconds(getattr(item, "start_time", 0.0))),
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best = item
        return best if best_overlap > 0.0 else None

    def _first_number(self, field_name: str, *items: object, fallback: float = 0.0) -> float:
        for item in items:
            if item is None:
                continue
            value = getattr(item, field_name, None)
            if value is not None:
                return self._seconds(value, fallback=fallback)
        return self._seconds(fallback)

    def _first_text(self, field_name: str, *items: object, fallback: str = "") -> str:
        for item in items:
            if item is None:
                continue
            value = getattr(item, field_name, None)
            if value:
                return str(value)
        return fallback

    def _field(self, item: object | None, name: str, fallback: float = 0.0) -> float:
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

    def _dedupe(self, values: list[str], *, limit: int) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            text = str(value or "")
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
            if len(result) >= limit:
                break
        return result

    def _log(self, report: Phase2BFinalReviewReport) -> None:
        print(
            "[PHASE-2B-FINAL-REVIEW] "
            f"segments={report.total_segments} "
            f"strong_keep={report.strong_keep} "
            f"boundary_warning={report.keep_with_boundary_warning} "
            f"review={report.review_needed} "
            f"edge_trim={report.possible_edge_trim_later} "
            f"safe={report.safe} "
            f"high={report.high_priority_reviews} "
            f"medium={report.medium_priority_reviews}"
        )
