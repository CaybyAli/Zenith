from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from models.learning_pattern_recognition import (
    LearningFeedbackTrend,
    LearningPatternCluster,
    LearningPatternRecognitionReport,
)

STATUS_WAITING = "learning_pattern_waiting_for_feedback"
STATUS_READY = "learning_pattern_ready"
STATUS_READY_WITH_WARNINGS = "learning_pattern_ready_with_warnings"
STATUS_BLOCKED = "learning_pattern_blocked"
STATUS_FAILED = "learning_pattern_failed"

TREND_REPEATED_ISSUE = "repeated_issue"
TREND_REPEATED_SUCCESS = "repeated_success"
TREND_MIXED_SIGNAL = "mixed_signal"
TREND_SINGLE_JOB = "single_job_observation"

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"

RECOMMENDATION_REVIEW = "review_learning_pattern_recognition"
RECOMMENDATION_WAIT = "collect_feedback_before_learning_pattern_recognition"
RECOMMENDATION_FIX_BLOCKERS = "fix_learning_pattern_blockers"

WARNING_SINGLE_JOB_ONLY = "learning_pattern_history_missing_single_job_only"

BLOCKING_FIELDS = (
    "feedback_blocking_reasons",
    "style_dna_update_blocking_reasons",
    "style_dna_review_blocking_reasons",
    "style_dna_apply_blocking_reasons",
    "style_dna_persistence_blocking_reasons",
)

BLOCKING_FEEDBACK_STATUSES = {
    "feedback_intake_blocked",
    "feedback_intake_failed",
}

WAITING_FEEDBACK_STATUSES = {
    "feedback_intake_waiting_for_feedback",
    "waiting_for_feedback",
}

POSITIVE_TAGS = {
    "good_cut",
    "strong_hook",
    "good_pacing",
    "good_reaction",
    "good_censor",
    "good_audio",
    "good_segment_length",
    "good_render_quality",
    "good_output_format",
}

NEGATIVE_TAGS = {
    "bad_pacing",
    "wrong_hook",
    "missing_reaction",
    "segment_too_long",
    "segment_too_short",
    "audio_too_loud",
    "audio_too_quiet",
    "sentence_cut_violation",
    "wrong_censor",
    "render_quality_issue",
    "output_format_issue",
}

TAG_CLUSTER_RULES = {
    "bad_pacing": (
        "pacing_pattern",
        (
            "preferred_avg_clip_duration",
            "pacing_sensitivity",
            "breathing_room_preference",
        ),
    ),
    "good_pacing": (
        "pacing_pattern",
        (
            "preferred_avg_clip_duration",
            "pacing_sensitivity",
            "breathing_room_preference",
        ),
    ),
    "wrong_hook": (
        "hook_pattern",
        (
            "preferred_hook_energy_min",
            "hook_confidence_threshold",
            "hook_strategy_confidence",
        ),
    ),
    "strong_hook": (
        "hook_pattern",
        (
            "preferred_hook_energy_min",
            "hook_confidence_threshold",
            "hook_strategy_confidence",
        ),
    ),
    "missing_reaction": (
        "reaction_pattern",
        (
            "reaction_shot_priority",
            "reaction_shot_preferred_duration",
        ),
    ),
    "good_reaction": (
        "reaction_pattern",
        (
            "reaction_shot_priority",
            "reaction_shot_preferred_duration",
        ),
    ),
    "segment_too_long": (
        "segment_length_pattern",
        (
            "max_segment_duration_sec",
            "min_segment_duration_sec",
            "preferred_avg_clip_duration",
        ),
    ),
    "segment_too_short": (
        "segment_length_pattern",
        (
            "max_segment_duration_sec",
            "min_segment_duration_sec",
            "preferred_avg_clip_duration",
        ),
    ),
    "audio_too_loud": (
        "audio_pattern",
        ("target_voice_gain_db",),
    ),
    "audio_too_quiet": (
        "audio_pattern",
        ("target_voice_gain_db",),
    ),
    "sentence_cut_violation": (
        "sentence_boundary_pattern",
        (
            "sentence_boundary_strictness",
            "max_cut_shift_ms",
        ),
    ),
    "wrong_censor": (
        "censor_pattern",
        ("censor_sfx_sensitivity",),
    ),
    "good_censor": (
        "censor_pattern",
        ("censor_sfx_sensitivity",),
    ),
    "render_quality_issue": (
        "render_quality_pattern",
        ("render_quality_review_required",),
    ),
    "output_format_issue": (
        "output_format_pattern",
        ("output_format_review_required",),
    ),
}

CLUSTER_TITLES = {
    "hook_pattern": "Hook Pattern",
    "pacing_pattern": "Pacing Pattern",
    "reaction_pattern": "Reaction Pattern",
    "audio_pattern": "Audio Pattern",
    "segment_length_pattern": "Segment Length Pattern",
    "sentence_boundary_pattern": "Sentence Boundary Pattern",
    "censor_pattern": "Censor Pattern",
    "render_quality_pattern": "Render Quality Pattern",
    "output_format_pattern": "Output Format Pattern",
    "general_feedback_pattern": "General Feedback Pattern",
}

SAFETY_METADATA = {
    "phase": "2B-64",
    "block": "block9_learning_feedback",
    "learning_pattern_recognition_only": True,
    "feedback_trend_analysis_only": True,
    "no_style_dna_file_write_in_2b_64": True,
    "no_profile_change_in_2b_64": True,
    "no_cutting_rule_activation_in_2b_64": True,
    "no_timeline_modify_in_2b_64": True,
    "no_render_trigger_in_2b_64": True,
    "no_publish_in_2b_64": True,
}


def build_learning_pattern_recognition_report(job: Any) -> dict[str, Any]:
    try:
        return _build_report(job)
    except Exception as exc:
        return _empty_report(
            job=job,
            status=STATUS_FAILED,
            warnings=[str(exc)],
            blocking_reasons=[str(exc)],
            recommendation=RECOMMENDATION_REVIEW,
        )


def _build_report(job: Any) -> dict[str, Any]:
    job_id = _string_or_none(_job_attr(job, "job_id"))
    profile = _string_or_none(
        _job_attr(job, "style_dna_profile_name")
        or _job_attr(job, "profile_id")
        or _job_attr(job, "profile")
    )
    feedback_status = _string_or_none(_job_attr(job, "feedback_intake_status"))

    min_occurrences = max(
        1,
        _safe_int(_job_attr(job, "learning_pattern_min_occurrences", 2), 2),
    )
    min_confidence = max(
        0.0,
        min(
            1.0,
            _safe_float(_job_attr(job, "learning_pattern_min_confidence", 0.50), 0.50),
        ),
    )

    blocking_reasons = _collect_blocking_reasons(job)
    if feedback_status in BLOCKING_FEEDBACK_STATUSES:
        blocking_reasons.append(f"source_feedback_status_{feedback_status}")

    if blocking_reasons:
        return _empty_report(
            job=job,
            status=STATUS_BLOCKED,
            warnings=[],
            blocking_reasons=_dedupe(blocking_reasons),
            recommendation=RECOMMENDATION_FIX_BLOCKERS,
        )

    evidence = _collect_all_evidence(job)
    feedback_sample_count = sum(item["count"] for item in evidence)

    if not evidence or (
        feedback_status in WAITING_FEEDBACK_STATUSES
        and _safe_int(_job_attr(job, "feedback_submission_count", 0), 0) <= 0
        and feedback_sample_count <= 0
    ):
        return _empty_report(
            job=job,
            status=STATUS_WAITING,
            warnings=[],
            blocking_reasons=[],
            recommendation=RECOMMENDATION_WAIT,
        )

    warnings: list[str] = []
    history_present = bool(_job_attr(job, "feedback_history_snapshot")) or bool(
        _job_attr(job, "style_dna_learning_history_snapshot")
    )
    if not history_present:
        warnings.append(WARNING_SINGLE_JOB_ONLY)

    trends = _build_trends(
        evidence=evidence,
        min_occurrences=min_occurrences,
    )
    clusters = _build_clusters(
        evidence=evidence,
        min_occurrences=min_occurrences,
        min_confidence=min_confidence,
    )

    repeated_issue_count = sum(
        1 for trend in trends if trend.trend_type == TREND_REPEATED_ISSUE
    )
    repeated_success_count = sum(
        1 for trend in trends if trend.trend_type == TREND_REPEATED_SUCCESS
    )

    top_negative_patterns = [
        trend.tag or trend.category or trend.trend_id
        for trend in sorted(
            [item for item in trends if item.trend_type == TREND_REPEATED_ISSUE],
            key=lambda item: (item.confidence, item.occurrence_count),
            reverse=True,
        )[:5]
    ]
    top_positive_patterns = [
        trend.tag or trend.category or trend.trend_id
        for trend in sorted(
            [item for item in trends if item.trend_type == TREND_REPEATED_SUCCESS],
            key=lambda item: (item.confidence, item.occurrence_count),
            reverse=True,
        )[:5]
    ]

    confidence = _overall_confidence(clusters, trends)
    overfitting_risk = _overall_risk(clusters, trends)
    ready_for_future_style_dna_proposal = bool(
        clusters
        and not blocking_reasons
        and confidence >= min_confidence
        and overfitting_risk != RISK_HIGH
        and any(cluster.safe_to_use_for_future_proposal for cluster in clusters)
    )

    status = STATUS_READY_WITH_WARNINGS if warnings else STATUS_READY

    report = LearningPatternRecognitionReport(
        report_id=f"lpr_{uuid4().hex[:12]}",
        job_id=job_id,
        status=status,
        profile=profile,
        source_feedback_status=feedback_status,
        feedback_sample_count=feedback_sample_count,
        trend_count=len(trends),
        cluster_count=len(clusters),
        trends=trends,
        clusters=clusters,
        top_positive_patterns=top_positive_patterns,
        top_negative_patterns=top_negative_patterns,
        repeated_issue_count=repeated_issue_count,
        repeated_success_count=repeated_success_count,
        confidence=confidence,
        overfitting_risk=overfitting_risk,
        ready_for_future_style_dna_proposal=ready_for_future_style_dna_proposal,
        can_update_style_dna=False,
        can_write_style_dna=False,
        can_change_profile=False,
        can_change_cutting_rules=False,
        can_modify_timeline=False,
        can_trigger_render=False,
        can_publish=False,
        warnings=warnings,
        blocking_reasons=[],
        recommendation=RECOMMENDATION_REVIEW,
        created_at=_utc_now_iso(),
        metadata={
            **SAFETY_METADATA,
            "min_occurrences": min_occurrences,
            "min_confidence": min_confidence,
            "history_present": history_present,
        },
    )
    return report.to_dict()


def _empty_report(
    *,
    job: Any,
    status: str,
    warnings: list[str],
    blocking_reasons: list[str],
    recommendation: str,
) -> dict[str, Any]:
    report = LearningPatternRecognitionReport(
        report_id=f"lpr_{uuid4().hex[:12]}",
        job_id=_string_or_none(_job_attr(job, "job_id")),
        status=status,
        profile=_string_or_none(
            _job_attr(job, "style_dna_profile_name")
            or _job_attr(job, "profile_id")
            or _job_attr(job, "profile")
        ),
        source_feedback_status=_string_or_none(_job_attr(job, "feedback_intake_status")),
        feedback_sample_count=0,
        trend_count=0,
        cluster_count=0,
        trends=[],
        clusters=[],
        top_positive_patterns=[],
        top_negative_patterns=[],
        repeated_issue_count=0,
        repeated_success_count=0,
        confidence=0.0,
        overfitting_risk=RISK_HIGH if blocking_reasons else RISK_MEDIUM,
        ready_for_future_style_dna_proposal=False,
        can_update_style_dna=False,
        can_write_style_dna=False,
        can_change_profile=False,
        can_change_cutting_rules=False,
        can_modify_timeline=False,
        can_trigger_render=False,
        can_publish=False,
        warnings=_dedupe(warnings),
        blocking_reasons=_dedupe(blocking_reasons),
        recommendation=recommendation,
        created_at=_utc_now_iso(),
        metadata=dict(SAFETY_METADATA),
    )
    return report.to_dict()


def _collect_all_evidence(job: Any) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    current_job_id = _string_or_none(_job_attr(job, "job_id"))

    _add_summary_evidence(
        evidence,
        tags_summary=_job_attr(job, "feedback_tags_summary", {}),
        category_summary=_job_attr(job, "feedback_category_summary", {}),
        job_id=current_job_id,
        source="feedback_summary",
    )

    for submission in _safe_list(_job_attr(job, "feedback_submissions", [])):
        _add_submission_evidence(
            evidence,
            submission=submission,
            fallback_job_id=current_job_id,
            source="feedback_submission",
        )

    for snapshot_name in (
        "feedback_history_snapshot",
        "style_dna_learning_history_snapshot",
    ):
        for entry in _iter_snapshot_entries(_job_attr(job, snapshot_name, [])):
            if not isinstance(entry, dict):
                continue
            entry_job_id = _string_or_none(entry.get("job_id")) or current_job_id
            _add_summary_evidence(
                evidence,
                tags_summary=entry.get("feedback_tags_summary")
                or entry.get("tags_summary")
                or {},
                category_summary=entry.get("feedback_category_summary")
                or entry.get("category_summary")
                or {},
                job_id=entry_job_id,
                source=snapshot_name,
            )
            _add_submission_evidence(
                evidence,
                submission=entry,
                fallback_job_id=entry_job_id,
                source=snapshot_name,
            )

    for proposal in _safe_list(_job_attr(job, "style_dna_update_proposals", [])):
        _add_proposal_evidence(
            evidence,
            proposal=proposal,
            fallback_job_id=current_job_id,
            source="style_dna_update_proposal",
        )

    for operation in _safe_list(_job_attr(job, "style_dna_apply_operations", [])):
        _add_proposal_evidence(
            evidence,
            proposal=operation,
            fallback_job_id=current_job_id,
            source="style_dna_apply_operation",
        )

    return [item for item in evidence if item["count"] > 0]


def _add_summary_evidence(
    evidence: list[dict[str, Any]],
    *,
    tags_summary: Any,
    category_summary: Any,
    job_id: str | None,
    source: str,
) -> None:
    if isinstance(tags_summary, dict):
        for tag, count in tags_summary.items():
            normalized_tag = _normalize_key(tag)
            if not normalized_tag:
                continue
            evidence.append(
                _evidence_item(
                    tag=normalized_tag,
                    category=None,
                    count=_safe_int(count, 0),
                    job_id=job_id,
                    sentiment=_sentiment_for_tag(normalized_tag),
                    score=None,
                    source=source,
                )
            )

    if isinstance(category_summary, dict):
        for category, count in category_summary.items():
            normalized_category = _normalize_key(category)
            if not normalized_category:
                continue
            evidence.append(
                _evidence_item(
                    tag=None,
                    category=normalized_category,
                    count=_safe_int(count, 0),
                    job_id=job_id,
                    sentiment="neutral",
                    score=None,
                    source=source,
                )
            )


def _add_submission_evidence(
    evidence: list[dict[str, Any]],
    *,
    submission: Any,
    fallback_job_id: str | None,
    source: str,
) -> None:
    if not isinstance(submission, dict):
        return

    job_id = _string_or_none(submission.get("job_id")) or fallback_job_id
    category = _normalize_key(
        submission.get("category") or submission.get("feedback_category")
    )
    score = _optional_float(
        submission.get("video_score")
        or submission.get("feedback_video_score")
        or submission.get("score")
    )
    explicit_sentiment = _normalize_sentiment(
        submission.get("sentiment")
        or submission.get("feedback_sentiment")
        or submission.get("rating")
    )

    tags = _tags_from_value(
        submission.get("tags")
        or submission.get("feedback_tags")
        or submission.get("tag")
    )
    if not tags and category:
        evidence.append(
            _evidence_item(
                tag=None,
                category=category,
                count=1,
                job_id=job_id,
                sentiment=explicit_sentiment or _sentiment_from_score(score),
                score=score,
                source=source,
            )
        )
        return

    for tag in tags:
        evidence.append(
            _evidence_item(
                tag=tag,
                category=category,
                count=1,
                job_id=job_id,
                sentiment=explicit_sentiment
                or _sentiment_for_tag(tag)
                or _sentiment_from_score(score),
                score=score,
                source=source,
            )
        )


def _add_proposal_evidence(
    evidence: list[dict[str, Any]],
    *,
    proposal: Any,
    fallback_job_id: str | None,
    source: str,
) -> None:
    if not isinstance(proposal, dict):
        return

    tags = _tags_from_value(
        proposal.get("source_tags")
        or proposal.get("feedback_tags")
        or proposal.get("tags")
        or proposal.get("tag")
    )
    category = _normalize_key(
        proposal.get("category")
        or proposal.get("source_category")
        or proposal.get("feedback_category")
    )
    job_id = _string_or_none(proposal.get("job_id")) or fallback_job_id
    confidence = _optional_float(proposal.get("confidence"))

    for tag in tags:
        evidence.append(
            _evidence_item(
                tag=tag,
                category=category,
                count=1,
                job_id=job_id,
                sentiment=_sentiment_for_tag(tag) or "neutral",
                score=confidence,
                source=source,
            )
        )


def _build_trends(
    *,
    evidence: list[dict[str, Any]],
    min_occurrences: int,
) -> list[LearningFeedbackTrend]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in evidence:
        key = item["tag"] or f"category:{item['category']}"
        grouped.setdefault(key, []).append(item)

    trends: list[LearningFeedbackTrend] = []
    for key in sorted(grouped):
        items = grouped[key]
        occurrence_count = sum(item["count"] for item in items)
        positive_count = sum(
            item["count"] for item in items if item["sentiment"] == "positive"
        )
        negative_count = sum(
            item["count"] for item in items if item["sentiment"] == "negative"
        )
        neutral_count = max(0, occurrence_count - positive_count - negative_count)
        job_ids = [
            item["job_id"]
            for item in items
            if item.get("job_id") is not None
        ]
        unique_job_count = len(set(job_ids))
        trend_type = _trend_type(
            occurrence_count=occurrence_count,
            positive_count=positive_count,
            negative_count=negative_count,
            min_occurrences=min_occurrences,
        )
        overfitting_risk = _risk_for_pattern(
            occurrence_count=occurrence_count,
            unique_job_count=unique_job_count,
            trend_type=trend_type,
            min_occurrences=min_occurrences,
        )
        confidence = _confidence_for_pattern(
            occurrence_count=occurrence_count,
            unique_job_count=unique_job_count,
            trend_type=trend_type,
            overfitting_risk=overfitting_risk,
        )

        tag = items[0]["tag"]
        category = items[0]["category"]
        trends.append(
            LearningFeedbackTrend(
                trend_id=f"lft_{_safe_id(key)}",
                trend_type=trend_type,
                tag=tag,
                category=category,
                occurrence_count=occurrence_count,
                positive_count=positive_count,
                negative_count=negative_count,
                neutral_count=neutral_count,
                average_score=_average_score(items),
                confidence=confidence,
                severity=_severity_for_trend(trend_type, occurrence_count),
                first_seen_job_id=job_ids[0] if job_ids else None,
                latest_seen_job_id=job_ids[-1] if job_ids else None,
                warnings=(
                    ["learning_pattern_mixed_signal_confidence_limited"]
                    if trend_type == TREND_MIXED_SIGNAL
                    else []
                ),
                blocking_reasons=[],
                metadata={
                    "source_count": len(items),
                    "unique_job_count": unique_job_count,
                    "overfitting_risk": overfitting_risk,
                    "sources": _dedupe([item["source"] for item in items]),
                },
            )
        )

    return trends


def _build_clusters(
    *,
    evidence: list[dict[str, Any]],
    min_occurrences: int,
    min_confidence: float,
) -> list[LearningPatternCluster]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in evidence:
        tag = item.get("tag")
        if not tag:
            continue
        cluster_type, _parameters = TAG_CLUSTER_RULES.get(
            tag,
            ("general_feedback_pattern", ()),
        )
        grouped.setdefault(cluster_type, []).append(item)

    clusters: list[LearningPatternCluster] = []
    for cluster_type in sorted(grouped):
        items = grouped[cluster_type]
        occurrence_count = sum(item["count"] for item in items)
        positive_count = sum(
            item["count"] for item in items if item["sentiment"] == "positive"
        )
        negative_count = sum(
            item["count"] for item in items if item["sentiment"] == "negative"
        )
        job_ids = [
            item["job_id"]
            for item in items
            if item.get("job_id") is not None
        ]
        unique_job_count = len(set(job_ids))
        source_tags = _dedupe(
            [str(item["tag"]) for item in items if item.get("tag")]
        )
        source_categories = _dedupe(
            [str(item["category"]) for item in items if item.get("category")]
        )
        trend_type = _trend_type(
            occurrence_count=occurrence_count,
            positive_count=positive_count,
            negative_count=negative_count,
            min_occurrences=min_occurrences,
        )
        risk = _risk_for_pattern(
            occurrence_count=occurrence_count,
            unique_job_count=unique_job_count,
            trend_type=trend_type,
            min_occurrences=min_occurrences,
        )
        confidence = _confidence_for_pattern(
            occurrence_count=occurrence_count,
            unique_job_count=unique_job_count,
            trend_type=trend_type,
            overfitting_risk=risk,
        )
        affected_parameters = _affected_parameters_for_tags(source_tags)
        safe_to_use = bool(
            occurrence_count >= min_occurrences
            and confidence >= min_confidence
            and risk != RISK_HIGH
        )

        clusters.append(
            LearningPatternCluster(
                cluster_id=f"lpc_{_safe_id(cluster_type)}",
                cluster_type=cluster_type,
                title=CLUSTER_TITLES.get(cluster_type, "Learning Pattern"),
                description=_cluster_description(
                    cluster_type=cluster_type,
                    occurrence_count=occurrence_count,
                    positive_count=positive_count,
                    negative_count=negative_count,
                ),
                source_tags=source_tags,
                source_categories=source_categories,
                affected_parameters=affected_parameters,
                occurrence_count=occurrence_count,
                confidence=confidence,
                overfitting_risk=risk,
                recommendation=_cluster_recommendation(cluster_type, trend_type),
                safe_to_use_for_future_proposal=safe_to_use,
                warnings=(
                    ["learning_pattern_overfitting_risk_detected"]
                    if risk == RISK_HIGH
                    else []
                ),
                blocking_reasons=[],
                metadata={
                    "trend_type": trend_type,
                    "positive_count": positive_count,
                    "negative_count": negative_count,
                    "unique_job_count": unique_job_count,
                    "sources": _dedupe([item["source"] for item in items]),
                },
            )
        )

    return clusters


def _trend_type(
    *,
    occurrence_count: int,
    positive_count: int,
    negative_count: int,
    min_occurrences: int,
) -> str:
    if positive_count > 0 and negative_count > 0:
        return TREND_MIXED_SIGNAL
    if occurrence_count >= min_occurrences and negative_count > positive_count:
        return TREND_REPEATED_ISSUE
    if occurrence_count >= min_occurrences and positive_count > negative_count:
        return TREND_REPEATED_SUCCESS
    return TREND_SINGLE_JOB


def _confidence_for_pattern(
    *,
    occurrence_count: int,
    unique_job_count: int,
    trend_type: str,
    overfitting_risk: str,
) -> float:
    confidence = min(0.95, 0.35 + occurrence_count * 0.10)
    if unique_job_count <= 1:
        confidence = min(confidence, 0.60)
    if trend_type == TREND_MIXED_SIGNAL:
        confidence = min(confidence, 0.55)
    if overfitting_risk == RISK_HIGH:
        confidence = min(confidence, 0.50)
    return round(confidence, 4)


def _risk_for_pattern(
    *,
    occurrence_count: int,
    unique_job_count: int,
    trend_type: str,
    min_occurrences: int,
) -> str:
    if trend_type == TREND_MIXED_SIGNAL:
        return RISK_HIGH
    if unique_job_count <= 1 and occurrence_count < min_occurrences:
        return RISK_HIGH
    if unique_job_count <= 1:
        return RISK_MEDIUM
    if occurrence_count < min_occurrences:
        return RISK_MEDIUM
    if unique_job_count >= 3 and occurrence_count >= 4:
        return RISK_LOW
    return RISK_MEDIUM


def _severity_for_trend(trend_type: str, occurrence_count: int) -> str:
    if trend_type == TREND_REPEATED_ISSUE and occurrence_count >= 5:
        return "high"
    if trend_type == TREND_REPEATED_ISSUE:
        return "medium"
    if trend_type == TREND_MIXED_SIGNAL:
        return "medium"
    if trend_type == TREND_REPEATED_SUCCESS:
        return "info"
    return "low"


def _cluster_description(
    *,
    cluster_type: str,
    occurrence_count: int,
    positive_count: int,
    negative_count: int,
) -> str:
    return (
        f"{CLUSTER_TITLES.get(cluster_type, 'Learning Pattern')} erkannt: "
        f"{occurrence_count} Hinweise, "
        f"{positive_count} positiv, {negative_count} negativ."
    )


def _cluster_recommendation(cluster_type: str, trend_type: str) -> str:
    if trend_type == TREND_REPEATED_ISSUE:
        return f"prepare_future_style_dna_proposal_for_{cluster_type}"
    if trend_type == TREND_REPEATED_SUCCESS:
        return f"preserve_future_style_dna_preference_for_{cluster_type}"
    if trend_type == TREND_MIXED_SIGNAL:
        return f"review_mixed_feedback_before_proposal_for_{cluster_type}"
    return f"watch_more_feedback_for_{cluster_type}"


def _affected_parameters_for_tags(tags: list[str]) -> list[str]:
    parameters: list[str] = []
    for tag in tags:
        _cluster_type, tag_parameters = TAG_CLUSTER_RULES.get(tag, ("", ()))
        parameters.extend(tag_parameters)
    return _dedupe(parameters)


def _overall_confidence(
    clusters: list[LearningPatternCluster],
    trends: list[LearningFeedbackTrend],
) -> float:
    values = [item.confidence for item in clusters] or [item.confidence for item in trends]
    if not values:
        return 0.0
    return round(max(values), 4)


def _overall_risk(
    clusters: list[LearningPatternCluster],
    trends: list[LearningFeedbackTrend],
) -> str:
    risks = [item.overfitting_risk for item in clusters]
    risks.extend(
        str(item.metadata.get("overfitting_risk"))
        for item in trends
        if item.metadata.get("overfitting_risk")
    )
    if not risks:
        return RISK_MEDIUM
    if RISK_HIGH in risks:
        return RISK_HIGH
    if all(risk == RISK_LOW for risk in risks):
        return RISK_LOW
    return RISK_MEDIUM


def _collect_blocking_reasons(job: Any) -> list[str]:
    reasons: list[str] = []
    for field_name in BLOCKING_FIELDS:
        for reason in _safe_list(_job_attr(job, field_name, [])):
            text = str(reason).strip()
            if text:
                reasons.append(text)
    return reasons


def _iter_snapshot_entries(snapshot: Any) -> list[Any]:
    if isinstance(snapshot, list):
        return snapshot
    if isinstance(snapshot, dict):
        entries: list[Any] = []
        for key in ("entries", "items", "jobs", "feedback_submissions", "submissions"):
            value = snapshot.get(key)
            if isinstance(value, list):
                entries.extend(value)
        if entries:
            return entries
        return [snapshot]
    return []


def _evidence_item(
    *,
    tag: str | None,
    category: str | None,
    count: int,
    job_id: str | None,
    sentiment: str | None,
    score: float | None,
    source: str,
) -> dict[str, Any]:
    normalized_sentiment = _normalize_sentiment(sentiment) or "neutral"
    return {
        "tag": tag,
        "category": category,
        "count": max(0, int(count or 0)),
        "job_id": job_id,
        "sentiment": normalized_sentiment,
        "score": score,
        "source": source,
    }


def _sentiment_for_tag(tag: str | None) -> str | None:
    if not tag:
        return None
    if tag in POSITIVE_TAGS:
        return "positive"
    if tag in NEGATIVE_TAGS:
        return "negative"
    if tag.startswith("good_") or tag.startswith("strong_"):
        return "positive"
    if tag.startswith("bad_") or tag.startswith("wrong_") or tag.startswith("missing_"):
        return "negative"
    return None


def _sentiment_from_score(score: float | None) -> str:
    if score is None:
        return "neutral"
    if score >= 0.75:
        return "positive"
    if score <= 0.45:
        return "negative"
    return "neutral"


def _normalize_sentiment(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"positive", "good", "success", "approved", "like"}:
        return "positive"
    if text in {"negative", "bad", "issue", "rejected", "dislike"}:
        return "negative"
    if text in {"neutral", "mixed", "none"}:
        return "neutral"
    return None


def _tags_from_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.replace(";", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = [value]
    return _dedupe([_normalize_key(item) for item in raw_items if _normalize_key(item)])


def _average_score(items: list[dict[str, Any]]) -> float | None:
    score_sum = 0.0
    score_count = 0
    for item in items:
        score = item.get("score")
        if score is None:
            continue
        count = int(item.get("count", 1) or 1)
        score_sum += float(score) * count
        score_count += count
    if score_count <= 0:
        return None
    return round(score_sum / score_count, 4)


def _job_attr(job: Any, key: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(key, default)
    return getattr(job, key, default)


def _safe_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_key(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text or None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_id(value: Any) -> str:
    text = _normalize_key(value) or "unknown"
    return "".join(ch for ch in text if ch.isalnum() or ch == "_")[:80]


def _dedupe(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        marker = str(value)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return result


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
