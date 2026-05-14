from __future__ import annotations

from collections import Counter
from typing import Any

from models.feedback_intake import (
    FEEDBACK_STATUS_BLOCKED,
    FEEDBACK_STATUS_FAILED,
    FEEDBACK_STATUS_READY,
    FEEDBACK_STATUS_READY_WITH_WARNINGS,
    FEEDBACK_STATUS_WAITING,
    KNOWN_FEEDBACK_CATEGORIES,
    KNOWN_FEEDBACK_TAGS,
    SENTIMENT_NEGATIVE,
    SENTIMENT_NEUTRAL,
    SENTIMENT_POSITIVE,
    FeedbackIntakeReport,
    FeedbackSubmission,
    FeedbackTimestampItem,
    normalize_score,
    normalize_sentiment,
    normalize_severity,
    normalize_text,
    normalize_text_list,
    normalize_timestamp,
    utc_now_iso,
)


PHASE_METADATA = {
    "phase": "2B-59",
    "block": "block9_learning_feedback",
    "feedback_intake_only": True,
    "review_feedback_only": True,
    "no_style_" "dna_update_in_2b_59": True,
    "no_profile_change_in_2b_59": True,
    "no_cutting_rule_change_in_2b_59": True,
    "no_timeline_modify_in_2b_59": True,
    "no_" "render_trigger_in_2b_59": True,
    "no_publish_in_2b_59": True,
}


SCORE_FIELDS = [
    "video_score",
    "overall_quality_score",
    "hook_quality_score",
    "pacing_quality_score",
    "story_quality_score",
    "audio_quality_score",
    "visual_quality_score",
    "render_quality_score",
]


def build_feedback_intake_report(job: Any) -> FeedbackIntakeReport:
    job_id = normalize_text(_get(job, "job_id")) or normalize_text(_get(job, "id"))
    submissions = _collect_submissions(job, job_id)

    if not submissions:
        return FeedbackIntakeReport(
            report_id=_make_report_id(job_id),
            job_id=job_id,
            status=FEEDBACK_STATUS_WAITING,
            submissions=[],
            submission_count=0,
            timestamp_feedback_count=0,
            positive_feedback_count=0,
            negative_feedback_count=0,
            neutral_feedback_count=0,
            average_video_score=None,
            tags_summary={},
            category_summary={},
            review_required=True,
            ready_for_style_dna_update=False,
            can_update_style_dna=False,
            can_change_profile=False,
            can_change_cutting_rules=False,
            can_modify_timeline=False,
            can_trigger_render=False,
            can_publish=False,
            warnings=[],
            blocking_reasons=[],
            recommendation="Feedback wartet auf Review-Eingabe.",
            metadata=dict(PHASE_METADATA),
        )

    validated_submissions = [_validate_submission(item, index) for index, item in enumerate(submissions, start=1)]
    warnings: list[str] = []
    blocking_reasons: list[str] = []
    for submission in validated_submissions:
        warnings.extend(submission.warnings)
        blocking_reasons.extend(submission.blocking_reasons)

    valid_submissions = [submission for submission in validated_submissions if submission.valid]
    timestamp_count = sum(len(submission.timestamp_items) for submission in validated_submissions)
    positive_count, negative_count, neutral_count = _count_sentiments(validated_submissions)
    tags_summary = _build_tags_summary(validated_submissions)
    category_summary = _build_category_summary(validated_submissions)
    average_video_score = _average_score(validated_submissions)

    has_score = any(submission.video_score is not None for submission in valid_submissions)
    has_timestamp_feedback = any(submission.timestamp_items for submission in valid_submissions)
    ready_for_next_phase = bool(valid_submissions and not blocking_reasons and (has_score or has_timestamp_feedback))

    if blocking_reasons:
        status = FEEDBACK_STATUS_BLOCKED
        recommendation = "Feedback blockiert: bitte Blocking Reasons prüfen."
    elif warnings:
        status = FEEDBACK_STATUS_READY_WITH_WARNINGS
        recommendation = "Feedback ist nutzbar, aber Warnungen sollten geprüft werden."
    else:
        status = FEEDBACK_STATUS_READY
        recommendation = "Feedback Intake ist bereit für die spätere Feedback-Auswertung."

    return FeedbackIntakeReport(
        report_id=_make_report_id(job_id),
        job_id=job_id,
        status=status,
        submissions=validated_submissions,
        submission_count=len(validated_submissions),
        timestamp_feedback_count=timestamp_count,
        positive_feedback_count=positive_count,
        negative_feedback_count=negative_count,
        neutral_feedback_count=neutral_count,
        average_video_score=average_video_score,
        tags_summary=tags_summary,
        category_summary=category_summary,
        review_required=True,
        ready_for_style_dna_update=ready_for_next_phase,
        can_update_style_dna=False,
        can_change_profile=False,
        can_change_cutting_rules=False,
        can_modify_timeline=False,
        can_trigger_render=False,
        can_publish=False,
        warnings=_unique(warnings),
        blocking_reasons=_unique(blocking_reasons),
        recommendation=recommendation,
        metadata=dict(PHASE_METADATA),
    )


def _collect_submissions(job: Any, job_id: str | None) -> list[FeedbackSubmission]:
    raw_items: list[dict[str, Any]] = []

    feedback_submissions = _get(job, "feedback_submissions")
    if isinstance(feedback_submissions, list):
        raw_items.extend([item for item in feedback_submissions if isinstance(item, dict)])

    feedback_submission = _get(job, "feedback_submission")
    if isinstance(feedback_submission, dict):
        raw_items.append(feedback_submission)

    direct_submission = _build_direct_submission_from_job(job)
    if direct_submission:
        raw_items.append(direct_submission)

    submissions: list[FeedbackSubmission] = []
    for index, raw in enumerate(raw_items, start=1):
        payload = dict(raw)
        payload.setdefault("submission_id", f"feedback_submission_{index}")
        payload.setdefault("job_id", job_id)
        payload.setdefault("submitted_at", utc_now_iso())
        submissions.append(FeedbackSubmission.from_dict(payload))
    return submissions


def _build_direct_submission_from_job(job: Any) -> dict[str, Any] | None:
    has_direct_feedback = any(
        _get(job, name) not in (None, "", [], {})
        for name in [
            "feedback_video_score",
            "feedback_comment",
            "feedback_timestamp_items",
            "feedback_tags",
            "feedback_submitted_by",
            "feedback_submitted_at",
        ]
    )
    if not has_direct_feedback:
        return None

    return {
        "submission_id": "feedback_submission_direct",
        "video_score": _get(job, "feedback_video_score"),
        "comment": _get(job, "feedback_comment"),
        "timestamp_items": _get(job, "feedback_timestamp_items") or [],
        "tags": _get(job, "feedback_tags") or [],
        "submitted_by": _get(job, "feedback_submitted_by"),
        "submitted_at": _get(job, "feedback_submitted_at"),
    }


def _validate_submission(submission: FeedbackSubmission, index: int) -> FeedbackSubmission:
    submission.submission_id = submission.submission_id or f"feedback_submission_{index}"
    submission.submitted_at = submission.submitted_at or utc_now_iso()

    for field_name in SCORE_FIELDS:
        score = getattr(submission, field_name)
        normalized = normalize_score(score)
        setattr(submission, field_name, normalized)
        if normalized is not None and not 1.0 <= normalized <= 10.0:
            submission.blocking_reasons.append(f"{field_name}_outside_1_to_10")
            submission.valid = False

    if submission.video_score is None and submission.comment:
        submission.warnings.append("feedback_comment_without_video_score")

    submission.tags = _validate_tags(submission.tags, submission.warnings)
    submission.timestamp_items = [
        _validate_timestamp_item(item, item_index)
        for item_index, item in enumerate(submission.timestamp_items, start=1)
    ]

    for item in submission.timestamp_items:
        if item.warnings:
            submission.warnings.extend(item.warnings)
        if item.blocking_reasons:
            submission.blocking_reasons.extend(item.blocking_reasons)
            submission.valid = False

    return submission


def _validate_timestamp_item(item: FeedbackTimestampItem, index: int) -> FeedbackTimestampItem:
    item.item_id = item.item_id or f"feedback_timestamp_item_{index}"
    item.timestamp_seconds = normalize_timestamp(item.timestamp_seconds)
    item.start_seconds = normalize_timestamp(item.start_seconds)
    item.end_seconds = normalize_timestamp(item.end_seconds)
    item.sentiment = normalize_sentiment(item.sentiment)
    item.severity = normalize_severity(item.severity)

    if item.timestamp_seconds is None:
        item.blocking_reasons.append("timestamp_seconds_missing_or_invalid")
        item.valid = False
    elif item.timestamp_seconds < 0:
        item.blocking_reasons.append("timestamp_seconds_negative")
        item.valid = False

    if item.start_seconds is not None and item.start_seconds < 0:
        item.blocking_reasons.append("start_seconds_negative")
        item.valid = False

    if item.end_seconds is not None and item.end_seconds < 0:
        item.blocking_reasons.append("end_seconds_negative")
        item.valid = False

    if item.start_seconds is not None and item.end_seconds is not None and item.end_seconds < item.start_seconds:
        item.blocking_reasons.append("end_seconds_before_start_seconds")
        item.valid = False

    category = normalize_text(item.category)
    if category:
        item.category = category
        if category not in KNOWN_FEEDBACK_CATEGORIES:
            item.warnings.append(f"unknown_feedback_category:{category}")
            item.metadata["custom_category"] = True

    tag = normalize_text(item.tag)
    if tag:
        item.tag = tag
        if tag not in KNOWN_FEEDBACK_TAGS:
            item.warnings.append(f"unknown_feedback_tag:{tag}")
            item.metadata["custom_tag"] = True

    if item.sentiment == SENTIMENT_NEGATIVE and not item.comment:
        item.warnings.append("negative_feedback_without_comment")

    return item


def _validate_tags(tags: list[str], warnings: list[str]) -> list[str]:
    result: list[str] = []
    for tag in normalize_text_list(tags):
        result.append(tag)
        if tag not in KNOWN_FEEDBACK_TAGS:
            warnings.append(f"unknown_feedback_tag:{tag}")
    return result


def _count_sentiments(submissions: list[FeedbackSubmission]) -> tuple[int, int, int]:
    positive = 0
    negative = 0
    neutral = 0

    for submission in submissions:
        for item in submission.timestamp_items:
            if item.sentiment == SENTIMENT_POSITIVE:
                positive += 1
            elif item.sentiment == SENTIMENT_NEGATIVE:
                negative += 1
            else:
                neutral += 1

    return positive, negative, neutral


def _build_tags_summary(submissions: list[FeedbackSubmission]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for submission in submissions:
        counter.update(submission.tags)
        for item in submission.timestamp_items:
            if item.tag:
                counter[item.tag] += 1
    return dict(sorted(counter.items()))


def _build_category_summary(submissions: list[FeedbackSubmission]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for submission in submissions:
        for item in submission.timestamp_items:
            if item.category:
                counter[item.category] += 1
    return dict(sorted(counter.items()))


def _average_score(submissions: list[FeedbackSubmission]) -> float | None:
    scores = [submission.video_score for submission in submissions if submission.video_score is not None]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


def _make_report_id(job_id: str | None) -> str:
    base = job_id or "unknown_job"
    return f"feedback_intake_report_{base}"


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
