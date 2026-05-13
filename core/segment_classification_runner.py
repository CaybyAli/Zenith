from __future__ import annotations

from typing import Any

from core.segment_classifier import classify_segments_from_unified_signals
from models.segment_classification import STATUS_FAILED, STATUS_SKIPPED_NO_UNIFIED_SIGNALS
from models.segment_classification_run import SegmentClassificationRunReport


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


def _extract_signals_from_container(container: Any) -> list[Any]:
    if not container:
        return []

    if isinstance(container, list):
        return container

    if isinstance(container, tuple):
        return list(container)

    data = _object_to_dict(container)

    for key in (
        "signals",
        "unified_edit_signals",
        "edit_signals",
        "results",
        "items",
    ):
        value = data.get(key)
        if isinstance(value, list):
            return value

    nested_result = data.get("result")
    if nested_result is not None:
        nested_data = _object_to_dict(nested_result)
        for key in ("signals", "unified_edit_signals", "edit_signals"):
            value = nested_data.get(key)
            if isinstance(value, list):
                return value

    return []


def _read_unified_signals_from_job(job: Any) -> list[Any]:
    direct_signals = _extract_signals_from_container(
        _get_job_value(job, "unified_edit_signals")
    )
    if direct_signals:
        return direct_signals

    result_signals = _extract_signals_from_container(
        _get_job_value(job, "unified_edit_signal_result")
    )
    if result_signals:
        return result_signals

    summary_signals = _extract_signals_from_container(
        _get_job_value(job, "unified_edit_signal_summary")
    )
    if summary_signals:
        return summary_signals

    return []


def _build_report_from_result(
    result: Any,
    metadata: dict[str, Any] | None = None,
) -> SegmentClassificationRunReport:
    result_segments = list(getattr(result, "segments", []) or [])

    return SegmentClassificationRunReport(
        status=str(getattr(result, "status", "ok") or "ok"),
        source="segment_classifier",
        segment_classification_result=result,
        segments=result_segments,
        segment_count=int(getattr(result, "segment_count", len(result_segments)) or 0),
        highlight_count=int(getattr(result, "highlight_count", 0) or 0),
        hook_candidate_count=int(getattr(result, "hook_candidate_count", 0) or 0),
        protected_context_count=int(
            getattr(result, "protected_context_count", 0) or 0
        ),
        dead_candidate_count=int(getattr(result, "dead_candidate_count", 0) or 0),
        filler_count=int(getattr(result, "filler_count", 0) or 0),
        transition_count=int(getattr(result, "transition_count", 0) or 0),
        censor_required_count=int(getattr(result, "censor_required_count", 0) or 0),
        technical_warning_count=int(
            getattr(result, "technical_warning_count", 0) or 0
        ),
        recommendation=str(
            getattr(result, "recommendation", "review_segment_classification")
            or "review_segment_classification"
        ),
        warnings=list(getattr(result, "warnings", []) or []),
        errors=list(getattr(result, "errors", []) or []),
        metadata={
            **dict(getattr(result, "metadata", {}) or {}),
            **dict(metadata or {}),
        },
    )


def run_segment_classification_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> SegmentClassificationRunReport:
    run_metadata = dict(metadata or {})
    unified_signals = _read_unified_signals_from_job(job)

    if not unified_signals:
        result = classify_segments_from_unified_signals([], metadata=run_metadata)
        return _build_report_from_result(result, metadata=run_metadata)

    try:
        result = classify_segments_from_unified_signals(
            unified_signals,
            metadata=run_metadata,
        )
        return _build_report_from_result(result, metadata=run_metadata)
    except Exception as exc:
        return SegmentClassificationRunReport(
            status=STATUS_FAILED,
            source="segment_classifier",
            segment_classification_result=None,
            segments=[],
            segment_count=0,
            recommendation="segment_classification_failed",
            warnings=[],
            errors=[str(exc)],
            metadata=run_metadata,
        )


def apply_segment_classification_run_report_to_job(
    job: Any,
    report: SegmentClassificationRunReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = SegmentClassificationRunReport.from_dict(report)

    report_dict = report.to_dict()
    segment_dicts = [segment.to_dict() for segment in report.segments]

    _set_job_value(job, "segment_classification_report", report_dict)
    _set_job_value(job, "segment_classification_status", report.status)
    _set_job_value(job, "segment_classification_segments", segment_dicts)
    _set_job_value(job, "segment_classification_segment_count", report.segment_count)
    _set_job_value(job, "segment_classification_highlight_count", report.highlight_count)
    _set_job_value(
        job,
        "segment_classification_hook_candidate_count",
        report.hook_candidate_count,
    )
    _set_job_value(
        job,
        "segment_classification_protected_context_count",
        report.protected_context_count,
    )
    _set_job_value(
        job,
        "segment_classification_dead_candidate_count",
        report.dead_candidate_count,
    )
    _set_job_value(job, "segment_classification_filler_count", report.filler_count)
    _set_job_value(
        job,
        "segment_classification_transition_count",
        report.transition_count,
    )
    _set_job_value(
        job,
        "segment_classification_censor_required_count",
        report.censor_required_count,
    )
    _set_job_value(
        job,
        "segment_classification_technical_warning_count",
        report.technical_warning_count,
    )
    _set_job_value(job, "segment_classification_recommendation", report.recommendation)

    if report.status == STATUS_SKIPPED_NO_UNIFIED_SIGNALS:
        _set_job_value(
            job,
            "segment_classification_recommendation",
            "segment_classifier_skipped_no_unified_signals",
        )

    return job
