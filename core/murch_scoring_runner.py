from __future__ import annotations

from typing import Any

from core.murch_scoring_system import score_segments_with_murch
from models.murch_scoring import (
    STATUS_FAILED,
    STATUS_SKIPPED_NO_SEGMENTS,
)
from models.murch_scoring_run import MurchScoringRunReport


def _object_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    if hasattr(value, "to_dict"):
        try:
            converted = value.to_dict()
            if isinstance(converted, dict):
                return dict(converted)
        except Exception:
            return {}

    return {}


def _get_job_value(job: Any, key: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(key, default)

    return getattr(job, key, default)


def _set_job_value(job: Any, key: str, value: Any) -> None:
    if isinstance(job, dict):
        job[key] = value
        return

    setattr(job, key, value)


def _extract_list_from_container(container: Any, keys: tuple[str, ...]) -> list[Any]:
    if not container:
        return []

    if isinstance(container, list):
        return container

    if isinstance(container, tuple):
        return list(container)

    data = _object_to_dict(container)

    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value

    nested_result = data.get("result")
    if nested_result is not None:
        nested_data = _object_to_dict(nested_result)
        for key in keys:
            value = nested_data.get(key)
            if isinstance(value, list):
                return value

    return []


def _read_segment_classifications_from_job(job: Any) -> list[Any]:
    direct_segments = _extract_list_from_container(
        _get_job_value(job, "segment_classification_segments"),
        (
            "segments",
            "segment_classification_segments",
            "items",
            "results",
        ),
    )
    if direct_segments:
        return direct_segments

    report_segments = _extract_list_from_container(
        _get_job_value(job, "segment_classification_report"),
        (
            "segments",
            "segment_classification_segments",
            "items",
            "results",
        ),
    )
    if report_segments:
        return report_segments

    return []


def _read_unified_signals_from_job(job: Any) -> list[Any]:
    direct_signals = _extract_list_from_container(
        _get_job_value(job, "unified_edit_signals"),
        (
            "signals",
            "unified_edit_signals",
            "edit_signals",
            "items",
            "results",
        ),
    )
    if direct_signals:
        return direct_signals

    report_signals = _extract_list_from_container(
        _get_job_value(job, "unified_edit_signal_report"),
        (
            "signals",
            "unified_edit_signals",
            "edit_signals",
            "items",
            "results",
        ),
    )
    if report_signals:
        return report_signals

    summary_signals = _extract_list_from_container(
        _get_job_value(job, "unified_edit_signal_summary"),
        (
            "signals",
            "unified_edit_signals",
            "edit_signals",
            "items",
            "results",
        ),
    )
    if summary_signals:
        return summary_signals

    return []


def _build_report_from_result(
    result: Any,
    metadata: dict[str, Any] | None = None,
) -> MurchScoringRunReport:
    result_segment_scores = list(getattr(result, "segment_scores", []) or [])

    return MurchScoringRunReport(
        status=str(getattr(result, "status", "ok") or "ok"),
        source="murch_scoring",
        murch_scoring_result=result,
        segment_scores=result_segment_scores,
        segment_score_count=int(
            getattr(result, "segment_score_count", len(result_segment_scores)) or 0
        ),
        high_score_count=int(getattr(result, "high_score_count", 0) or 0),
        medium_score_count=int(getattr(result, "medium_score_count", 0) or 0),
        low_score_count=int(getattr(result, "low_score_count", 0) or 0),
        protected_context_count=int(
            getattr(result, "protected_context_count", 0) or 0
        ),
        censor_required_count=int(
            getattr(result, "censor_required_count", 0) or 0
        ),
        technical_warning_count=int(
            getattr(result, "technical_warning_count", 0) or 0
        ),
        avg_murch_score=float(getattr(result, "avg_murch_score", 0.0) or 0.0),
        max_murch_score=float(getattr(result, "max_murch_score", 0.0) or 0.0),
        min_murch_score=float(getattr(result, "min_murch_score", 0.0) or 0.0),
        recommendation=str(
            getattr(result, "recommendation", "review_murch_scoring_result")
            or "review_murch_scoring_result"
        ),
        warnings=list(getattr(result, "warnings", []) or []),
        errors=list(getattr(result, "errors", []) or []),
        metadata={
            **dict(getattr(result, "metadata", {}) or {}),
            **dict(metadata or {}),
        },
    )


def run_murch_scoring_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> MurchScoringRunReport:
    run_metadata = dict(metadata or {})
    segment_classifications = _read_segment_classifications_from_job(job)
    unified_signals = _read_unified_signals_from_job(job)

    if not segment_classifications:
        result = score_segments_with_murch([], metadata=run_metadata)
        report = _build_report_from_result(result, metadata=run_metadata)
        report.status = STATUS_SKIPPED_NO_SEGMENTS
        report.recommendation = "murch_scoring_skipped_no_segments"
        return report

    try:
        result = score_segments_with_murch(
            segment_classifications,
            unified_signals=unified_signals,
            metadata=run_metadata,
        )
        return _build_report_from_result(result, metadata=run_metadata)
    except Exception as exc:
        return MurchScoringRunReport(
            status=STATUS_FAILED,
            source="murch_scoring",
            murch_scoring_result=None,
            segment_scores=[],
            segment_score_count=0,
            recommendation="murch_scoring_failed",
            warnings=[],
            errors=[str(exc)],
            metadata=run_metadata,
        )


def apply_murch_scoring_run_report_to_job(
    job: Any,
    report: MurchScoringRunReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = MurchScoringRunReport.from_dict(report)

    report_dict = report.to_dict()
    segment_score_dicts = [
        segment_score.to_dict()
        for segment_score in report.segment_scores
    ]

    _set_job_value(job, "murch_scoring_report", report_dict)
    _set_job_value(job, "murch_scoring_status", report.status)
    _set_job_value(job, "murch_scoring_segment_scores", segment_score_dicts)
    _set_job_value(job, "murch_scoring_segment_score_count", report.segment_score_count)
    _set_job_value(job, "murch_scoring_high_score_count", report.high_score_count)
    _set_job_value(job, "murch_scoring_medium_score_count", report.medium_score_count)
    _set_job_value(job, "murch_scoring_low_score_count", report.low_score_count)
    _set_job_value(
        job,
        "murch_scoring_protected_context_count",
        report.protected_context_count,
    )
    _set_job_value(
        job,
        "murch_scoring_censor_required_count",
        report.censor_required_count,
    )
    _set_job_value(
        job,
        "murch_scoring_technical_warning_count",
        report.technical_warning_count,
    )
    _set_job_value(job, "murch_scoring_avg_score", report.avg_murch_score)
    _set_job_value(job, "murch_scoring_max_score", report.max_murch_score)
    _set_job_value(job, "murch_scoring_min_score", report.min_murch_score)
    _set_job_value(job, "murch_scoring_recommendation", report.recommendation)

    if report.status == STATUS_SKIPPED_NO_SEGMENTS:
        _set_job_value(
            job,
            "murch_scoring_recommendation",
            "murch_scoring_skipped_no_segments",
        )

    return job
