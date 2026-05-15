from __future__ import annotations

from collections import Counter
from typing import Any

from models.style_dna_feedback_update import (
    IMPACT_HIGH,
    IMPACT_LOW,
    IMPACT_MEDIUM,
    OVERFITTING_RISK_HIGH,
    OVERFITTING_RISK_LOW,
    OVERFITTING_RISK_MEDIUM,
    STYLE_DNA_STATUS_BLOCKED,
    STYLE_DNA_STATUS_DRAFT_READY,
    STYLE_DNA_STATUS_DRAFT_READY_WITH_WARNINGS,
    STYLE_DNA_STATUS_FAILED,
    STYLE_DNA_STATUS_WAITING,
    StyleDNAFeedbackUpdateReport,
    StyleDNAParameterProposal,
    StyleDNAUpdateDraft,
)


PHASE_METADATA = {
    "phase": "2B-60",
    "block": "block9_learning_feedback",
    "style_dna_update_proposal_only": True,
    "style_dna_draft_only": True,
    "no_style_dna_file_write_in_2b_60": True,
    "no_profile_change_in_2b_60": True,
    "no_cutting_rule_activation_in_2b_60": True,
    "no_timeline_modify_in_2b_60": True,
    "no_render_trigger_in_2b_60": True,
    "no_publish_in_2b_60": True,
}


FEEDBACK_STATUS_WAITING = "feedback_intake_waiting_for_feedback"
FEEDBACK_STATUS_BLOCKED = "feedback_intake_blocked"
FEEDBACK_STATUS_FAILED = "feedback_intake_failed"

FILE_LOCK_REASON = "style_dna_file_write_not_allowed_in_2b_60"

BLOCKING_FEEDBACK_FLAGS = [
    "feedback_can_update_style_dna",
    "feedback_can_change_profile",
    "feedback_can_modify_timeline",
    "feedback_can_trigger_render",
    "feedback_can_publish",
]


TAG_PROPOSAL_RULES = {
    "bad_pacing": [
        ("preferred_avg_clip_duration", -0.5, "Feedback meldet schlechtes Pacing. Vorschlag: durchschnittliche Clipdauer leicht senken.", IMPACT_MEDIUM),
        ("pacing_sensitivity", 0.05, "Feedback meldet schlechtes Pacing. Vorschlag: Pacing-Sensitivitaet leicht erhoehen.", IMPACT_MEDIUM),
    ],
    "good_pacing": [
        ("preferred_avg_clip_duration", 0.0, "Feedback lobt Pacing. Vorschlag: Wert stabil halten.", IMPACT_LOW),
        ("pacing_sensitivity", 0.0, "Feedback lobt Pacing. Vorschlag: Sensitivitaet stabil halten.", IMPACT_LOW),
    ],
    "wrong_hook": [
        ("preferred_hook_energy_min", 0.05, "Feedback meldet falschen Hook. Vorschlag: minimale Hook-Energie leicht erhoehen.", IMPACT_MEDIUM),
        ("hook_confidence_threshold", 0.05, "Feedback meldet falschen Hook. Vorschlag: Hook-Schwelle leicht erhoehen.", IMPACT_MEDIUM),
    ],
    "strong_hook": [
        ("preferred_hook_energy_min", 0.0, "Feedback lobt Hook. Vorschlag: Hook-Energie stabil halten.", IMPACT_LOW),
        ("hook_strategy_confidence", 0.03, "Feedback lobt Hook. Vorschlag: Hook-Strategie leicht staerken.", IMPACT_LOW),
    ],
    "segment_too_long": [
        ("max_segment_duration_sec", -2.0, "Feedback meldet zu langes Segment. Vorschlag: maximale Segmentdauer leicht senken.", IMPACT_MEDIUM),
        ("preferred_avg_clip_duration", -0.5, "Feedback meldet zu langes Segment. Vorschlag: durchschnittliche Clipdauer leicht senken.", IMPACT_MEDIUM),
    ],
    "segment_too_short": [
        ("min_segment_duration_sec", 1.0, "Feedback meldet zu kurzes Segment. Vorschlag: minimale Segmentdauer leicht erhoehen.", IMPACT_MEDIUM),
        ("breathing_room_preference", 0.05, "Feedback meldet zu kurzes Segment. Vorschlag: etwas mehr Atemraum bevorzugen.", IMPACT_MEDIUM),
    ],
    "missing_reaction": [
        ("reaction_shot_priority", 0.05, "Feedback meldet fehlende Reaction. Vorschlag: Reaction-Shots leicht hoeher priorisieren.", IMPACT_MEDIUM),
        ("reaction_shot_preferred_duration", 0.25, "Feedback meldet fehlende Reaction. Vorschlag: bevorzugte Reaction-Dauer leicht erhoehen.", IMPACT_MEDIUM),
    ],
    "good_reaction": [
        ("reaction_shot_priority", 0.0, "Feedback lobt Reaction-Shots. Vorschlag: Prioritaet stabil halten.", IMPACT_LOW),
        ("reaction_shot_preferred_duration", 0.0, "Feedback lobt Reaction-Shots. Vorschlag: Dauer stabil halten.", IMPACT_LOW),
    ],
    "audio_too_loud": [
        ("target_voice_gain_db", -0.75, "Feedback meldet zu laute Stimme. Vorschlag: Ziel-Gain leicht senken.", IMPACT_MEDIUM),
    ],
    "audio_too_quiet": [
        ("target_voice_gain_db", 0.75, "Feedback meldet zu leise Stimme. Vorschlag: Ziel-Gain leicht erhoehen.", IMPACT_MEDIUM),
    ],
    "boring_segment": [
        ("dead_content_aggressiveness", 0.05, "Feedback meldet langweiliges Segment. Vorschlag: Dead-Content-Erkennung leicht strenger machen.", IMPACT_MEDIUM),
        ("energy_floor", 0.05, "Feedback meldet langweiliges Segment. Vorschlag: Energie-Untergrenze leicht erhoehen.", IMPACT_MEDIUM),
    ],
    "sentence_cut_violation": [
        ("sentence_boundary_strictness", 0.05, "Feedback meldet Satzschnitt-Problem. Vorschlag: Satzgrenzen strenger beachten.", IMPACT_HIGH),
        ("max_cut_shift_ms", -100, "Feedback meldet Satzschnitt-Problem. Vorschlag: maximale Cut-Verschiebung leicht senken.", IMPACT_HIGH),
    ],
    "wrong_censor": [
        ("censor_sfx_sensitivity", "review", "Feedback meldet falschen Censor. Vorschlag: manuell pruefen, nicht automatisch aendern.", IMPACT_MEDIUM),
    ],
    "good_censor": [
        ("censor_sfx_sensitivity", 0.0, "Feedback lobt Censor. Vorschlag: Sensitivitaet stabil halten.", IMPACT_LOW),
    ],
    "render_quality_issue": [
        ("render_quality_review_required", True, "Feedback meldet Renderqualitaet. Vorschlag: Renderqualitaet manuell pruefen.", IMPACT_HIGH),
    ],
    "output_format_issue": [
        ("output_format_review_required", True, "Feedback meldet Output-Format. Vorschlag: Output-Format manuell pruefen.", IMPACT_HIGH),
    ],
}


def build_style_dna_feedback_update_report(job: Any) -> StyleDNAFeedbackUpdateReport:
    job_id = _text(_get(job, "job_id")) or _text(_get(job, "id"))
    profile = _resolve_profile(job)
    feedback_report = _get_feedback_report(job)
    feedback_status = _text(feedback_report.get("status")) or _text(_get(job, "feedback_intake_status"))

    warnings: list[str] = []
    blocking_reasons: list[str] = []

    if _get(job, "style_dna_update_allow_file_write", False):
        warnings.append(FILE_LOCK_REASON)

    if not feedback_report:
        return _waiting_report(
            job_id=job_id,
            profile=profile,
            source_feedback_status=feedback_status,
            warnings=warnings,
            recommendation="Style-DNA Update wartet auf Feedback Intake Report.",
        )

    intake_blockers = list(_get(job, "feedback_blocking_reasons") or [])
    intake_blockers.extend(list(feedback_report.get("blocking_reasons") or []))
    blocking_reasons.extend(_unique(intake_blockers))

    if feedback_status in {FEEDBACK_STATUS_BLOCKED, FEEDBACK_STATUS_FAILED}:
        blocking_reasons.append(f"feedback_intake_status_not_usable:{feedback_status}")

    for flag in BLOCKING_FEEDBACK_FLAGS:
        if bool(_get(job, flag, False)):
            blocking_reasons.append(f"unsafe_feedback_permission_flag_true:{flag}")

    if blocking_reasons:
        return _blocked_report(
            job_id=job_id,
            profile=profile,
            source_feedback_status=feedback_status,
            warnings=warnings,
            blocking_reasons=_unique(blocking_reasons),
            recommendation="Style-DNA Draft blockiert: Feedback Intake oder Safety Flags pruefen.",
        )

    submission_count = int(feedback_report.get("submission_count", _get(job, "feedback_submission_count", 0)) or 0)
    tags_summary = _collect_tags_summary(job, feedback_report)
    ready_for_next = bool(
        feedback_report.get(
            "ready_for_style_dna_update",
            _get(job, "feedback_ready_for_style_dna_update", False),
        )
    )

    if (
        submission_count <= 0
        or feedback_status == FEEDBACK_STATUS_WAITING
        or not ready_for_next
        or not tags_summary
    ):
        return _waiting_report(
            job_id=job_id,
            profile=profile,
            source_feedback_status=feedback_status,
            warnings=warnings,
            recommendation="Style-DNA Update wartet auf nutzbares Feedback mit Tags.",
        )

    average_score = _float_or_none(
        feedback_report.get("average_video_score", _get(job, "feedback_average_video_score"))
    )
    existing_snapshot = _get_existing_snapshot(job)
    proposals = _build_proposals(
        tags_summary=tags_summary,
        existing_snapshot=existing_snapshot,
        submission_count=submission_count,
        average_score=average_score,
    )

    if not proposals:
        warnings.append("no_supported_feedback_tags_for_style_dna_proposal")
        return _waiting_report(
            job_id=job_id,
            profile=profile,
            source_feedback_status=feedback_status,
            warnings=warnings,
            recommendation="Kein passender Style-DNA Vorschlag aus Feedback-Tags ableitbar.",
        )

    overfitting_risk = _calculate_overfitting_risk(
        submission_count=submission_count,
        tags_summary=tags_summary,
        average_score=average_score,
    )
    confidence = _calculate_report_confidence(
        proposals=proposals,
        submission_count=submission_count,
        average_score=average_score,
        overfitting_risk=overfitting_risk,
    )
    draft_warnings = list(warnings)
    if overfitting_risk in {OVERFITTING_RISK_MEDIUM, OVERFITTING_RISK_HIGH}:
        draft_warnings.append(f"overfitting_risk_{overfitting_risk}")

    draft = StyleDNAUpdateDraft(
        draft_id=f"style_dna_update_draft_{job_id or 'unknown_job'}",
        profile=profile,
        source_feedback_report_id=_text(feedback_report.get("report_id")),
        proposals=proposals,
        proposal_count=len(proposals),
        confidence=confidence,
        overfitting_risk=overfitting_risk,
        safe_to_review=True,
        warnings=_unique(draft_warnings),
        blocking_reasons=[],
        metadata={
            **PHASE_METADATA,
            "average_video_score": average_score,
            "submission_count": submission_count,
            "tag_count": sum(tags_summary.values()),
            "existing_snapshot_read": bool(existing_snapshot),
        },
    )

    status = (
        STYLE_DNA_STATUS_DRAFT_READY_WITH_WARNINGS
        if draft.warnings
        else STYLE_DNA_STATUS_DRAFT_READY
    )

    return StyleDNAFeedbackUpdateReport(
        report_id=f"style_dna_feedback_update_report_{job_id or 'unknown_job'}",
        job_id=job_id,
        status=status,
        profile=profile,
        source_feedback_status=feedback_status,
        draft=draft,
        proposal_count=len(proposals),
        accepted_feedback_count=submission_count,
        rejected_feedback_count=0,
        confidence=confidence,
        ready_for_human_review=True,
        ready_for_later_apply=bool(confidence >= 0.5 and not blocking_reasons),
        can_write_style_dna=False,
        can_update_profile=False,
        can_change_cutting_rules=False,
        can_modify_timeline=False,
        can_trigger_render=False,
        can_publish=False,
        warnings=_unique(draft.warnings),
        blocking_reasons=[],
        recommendation="Style-DNA Update Draft ist bereit fuer menschliche Pruefung.",
        metadata={
            **PHASE_METADATA,
            "style_dna_update_proposal_count": len(proposals),
            "overfitting_risk": overfitting_risk,
            "file_lock_reason": FILE_LOCK_REASON if FILE_LOCK_REASON in warnings else None,
        },
    )


def _build_proposals(
    *,
    tags_summary: dict[str, int],
    existing_snapshot: dict[str, Any],
    submission_count: int,
    average_score: float | None,
) -> list[StyleDNAParameterProposal]:
    proposals: list[StyleDNAParameterProposal] = []
    proposal_index = 1

    for tag, count in sorted(tags_summary.items()):
        rules = TAG_PROPOSAL_RULES.get(tag, [])
        for parameter_name, delta, reason, impact in rules:
            current_value = existing_snapshot.get(parameter_name)
            proposed_value = _proposed_value(current_value, delta)
            confidence = _proposal_confidence(
                tag_count=count,
                submission_count=submission_count,
                average_score=average_score,
                impact=impact,
            )
            proposals.append(
                StyleDNAParameterProposal(
                    proposal_id=f"style_dna_proposal_{proposal_index}",
                    parameter_name=parameter_name,
                    current_value=current_value,
                    proposed_value=proposed_value,
                    delta=delta,
                    reason=reason,
                    source_tags=[tag],
                    confidence=confidence,
                    impact=impact,
                    safe_to_apply_later=bool(confidence >= 0.5),
                    warnings=[],
                    blocking_reasons=[],
                    metadata={
                        **PHASE_METADATA,
                        "source_tag_count": count,
                        "proposal_only": True,
                        "existing_value_found": parameter_name in existing_snapshot,
                    },
                )
            )
            proposal_index += 1

    return proposals


def _proposed_value(current_value: Any, delta: Any) -> Any:
    if delta == "review":
        return "manual_review_required"
    if isinstance(delta, bool):
        return bool(delta)
    if isinstance(delta, (int, float)):
        if isinstance(current_value, (int, float)):
            return round(float(current_value) + float(delta), 3)
        if delta == 0:
            return "stabilize"
        return f"current_value_plus_{delta}"
    return delta


def _proposal_confidence(
    *,
    tag_count: int,
    submission_count: int,
    average_score: float | None,
    impact: str,
) -> float:
    confidence = 0.45
    confidence += min(max(tag_count - 1, 0) * 0.1, 0.25)

    if average_score is not None:
        if average_score >= 8:
            confidence += 0.05 if impact == IMPACT_LOW else -0.05
        elif average_score <= 5:
            confidence += 0.08 if impact in {IMPACT_MEDIUM, IMPACT_HIGH} else -0.02

    if submission_count <= 1:
        confidence = min(confidence, 0.6)
    else:
        confidence += min((submission_count - 1) * 0.04, 0.12)

    return round(max(0.0, min(confidence, 0.9)), 3)


def _calculate_report_confidence(
    *,
    proposals: list[StyleDNAParameterProposal],
    submission_count: int,
    average_score: float | None,
    overfitting_risk: str,
) -> float:
    if not proposals:
        return 0.0

    confidence = sum(item.confidence for item in proposals) / len(proposals)

    if overfitting_risk == OVERFITTING_RISK_HIGH:
        confidence -= 0.12
    elif overfitting_risk == OVERFITTING_RISK_MEDIUM:
        confidence -= 0.04

    if average_score is not None and average_score >= 8:
        confidence = min(confidence, 0.72)

    if submission_count <= 1:
        confidence = min(confidence, 0.6)

    return round(max(0.0, min(confidence, 0.9)), 3)


def _calculate_overfitting_risk(
    *,
    submission_count: int,
    tags_summary: dict[str, int],
    average_score: float | None,
) -> str:
    if submission_count <= 1:
        return OVERFITTING_RISK_MEDIUM

    total_tags = sum(tags_summary.values())
    repeated_tag_count = sum(1 for count in tags_summary.values() if count >= 2)

    if total_tags <= 1:
        return OVERFITTING_RISK_HIGH
    if average_score is not None and average_score >= 8 and repeated_tag_count == 0:
        return OVERFITTING_RISK_MEDIUM
    if repeated_tag_count >= 2 or submission_count >= 3:
        return OVERFITTING_RISK_LOW
    return OVERFITTING_RISK_MEDIUM


def _collect_tags_summary(job: Any, feedback_report: dict[str, Any]) -> dict[str, int]:
    raw = feedback_report.get("tags_summary")
    if isinstance(raw, dict) and raw:
        return {str(key): int(value or 0) for key, value in raw.items() if int(value or 0) > 0}

    job_tags = _get(job, "feedback_tags_summary")
    if isinstance(job_tags, dict) and job_tags:
        return {str(key): int(value or 0) for key, value in job_tags.items() if int(value or 0) > 0}

    counter: Counter[str] = Counter()
    for submission in list(feedback_report.get("submissions") or []):
        if not isinstance(submission, dict):
            continue
        counter.update([str(tag) for tag in list(submission.get("tags") or []) if tag])
        for item in list(submission.get("timestamp_items") or []):
            if isinstance(item, dict) and item.get("tag"):
                counter[str(item["tag"])] += 1
    return dict(sorted(counter.items()))


def _waiting_report(
    *,
    job_id: str | None,
    profile: str,
    source_feedback_status: str | None,
    warnings: list[str],
    recommendation: str,
) -> StyleDNAFeedbackUpdateReport:
    return StyleDNAFeedbackUpdateReport(
        report_id=f"style_dna_feedback_update_report_{job_id or 'unknown_job'}",
        job_id=job_id,
        status=STYLE_DNA_STATUS_WAITING,
        profile=profile,
        source_feedback_status=source_feedback_status,
        draft=None,
        proposal_count=0,
        accepted_feedback_count=0,
        rejected_feedback_count=0,
        confidence=0.0,
        ready_for_human_review=False,
        ready_for_later_apply=False,
        can_write_style_dna=False,
        can_update_profile=False,
        can_change_cutting_rules=False,
        can_modify_timeline=False,
        can_trigger_render=False,
        can_publish=False,
        warnings=_unique(warnings),
        blocking_reasons=[],
        recommendation=recommendation,
        metadata=dict(PHASE_METADATA),
    )


def _blocked_report(
    *,
    job_id: str | None,
    profile: str,
    source_feedback_status: str | None,
    warnings: list[str],
    blocking_reasons: list[str],
    recommendation: str,
) -> StyleDNAFeedbackUpdateReport:
    return StyleDNAFeedbackUpdateReport(
        report_id=f"style_dna_feedback_update_report_{job_id or 'unknown_job'}",
        job_id=job_id,
        status=STYLE_DNA_STATUS_BLOCKED,
        profile=profile,
        source_feedback_status=source_feedback_status,
        draft=None,
        proposal_count=0,
        accepted_feedback_count=0,
        rejected_feedback_count=len(blocking_reasons),
        confidence=0.0,
        ready_for_human_review=False,
        ready_for_later_apply=False,
        can_write_style_dna=False,
        can_update_profile=False,
        can_change_cutting_rules=False,
        can_modify_timeline=False,
        can_trigger_render=False,
        can_publish=False,
        warnings=_unique(warnings),
        blocking_reasons=_unique(blocking_reasons),
        recommendation=recommendation,
        metadata=dict(PHASE_METADATA),
    )


def _resolve_profile(job: Any) -> str:
    return (
        _text(_get(job, "style_dna_profile_name"))
        or _text(_get(job, "profile"))
        or _text(_get(job, "channel"))
        or "gaming_main"
    )


def _get_feedback_report(job: Any) -> dict[str, Any]:
    report = _get(job, "feedback_intake_report") or {}
    return report if isinstance(report, dict) else {}


def _get_existing_snapshot(job: Any) -> dict[str, Any]:
    snapshot = _get(job, "existing_style_dna_snapshot") or {}
    return snapshot if isinstance(snapshot, dict) else {}


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _unique(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)
