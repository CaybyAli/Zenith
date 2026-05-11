from __future__ import annotations

from typing import Any

from core.adaptive_silence_classifier import classify_silence_detection_result
from models.silence_classifier_run import SilenceClassifierRunReport


def build_silence_classifier_run_report(
    detection_result: Any,
    contexts: list[dict[str, Any]] | None = None,
    profile: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> SilenceClassifierRunReport:
    try:
        detection_status: str | None = None
        if isinstance(detection_result, dict):
            detection_status = detection_result.get("status")
        elif detection_result is not None:
            detection_status = getattr(detection_result, "status", None)

        if detection_result is None:
            return SilenceClassifierRunReport(
                status="failed",
                detection_status=detection_status,
                errors=["missing_detection_result"],
                recommendation="retry_or_fix_detection_result",
                metadata=dict(metadata or {}),
            )

        try:
            if isinstance(detection_result, dict):
                raw_segments = detection_result.get("segments", [])
                has_segments = isinstance(raw_segments, list) and len(raw_segments) > 0
            elif hasattr(detection_result, "segments"):
                segs = detection_result.segments
                has_segments = isinstance(segs, list) and len(segs) > 0
            else:
                has_segments = False
        except Exception:
            has_segments = False

        if not has_segments:
            return SilenceClassifierRunReport(
                status="skipped_no_silence_segments",
                detection_status=detection_status,
                classification_count=0,
                recommendation="no_silence_to_classify",
                metadata=dict(metadata or {}),
            )

        classification_result = classify_silence_detection_result(
            detection_result,
            contexts=contexts,
            profile=profile,
        )

        classification_result_dict = classification_result.to_dict()
        classifications = [c.to_dict() for c in classification_result.classifications]

        errors = list(classification_result.errors)
        warnings = list(classification_result.warnings)

        if errors:
            status = "failed"
            recommendation = "retry_or_fix_detection_result"
        elif warnings:
            status = "completed_with_warnings"
            recommendation = "review_warnings"
        elif classification_result.classification_count > 0:
            status = "ok"
            recommendation = "use_classification"
        else:
            status = "skipped_no_silence_segments"
            recommendation = "no_silence_to_classify"

        return SilenceClassifierRunReport(
            status=status,
            detection_status=detection_status,
            classification_status=classification_result.status,
            classification_result=classification_result_dict,
            classifications=classifications,
            classification_count=classification_result.classification_count,
            remove_candidate_count=classification_result.remove_candidate_count,
            keep_candidate_count=classification_result.keep_candidate_count,
            counts_by_classification=dict(classification_result.counts_by_classification),
            warnings=warnings,
            errors=errors,
            recommendation=recommendation,
            metadata=dict(metadata or {}),
        )

    except Exception as exc:
        return SilenceClassifierRunReport(
            status="failed",
            errors=[f"silence_classifier_runner_failed: {exc}"],
            recommendation="retry_or_fix_detection_result",
            metadata=dict(metadata or {}),
        )


def run_silence_classifier_for_job(
    job: Any,
    contexts: list[dict[str, Any]] | None = None,
    profile: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> SilenceClassifierRunReport:
    try:
        detection_result: Any = None

        raw = getattr(job, "silence_detection_result", None)
        if raw and isinstance(raw, dict) and len(raw) > 0:
            detection_result = raw
        elif raw and not isinstance(raw, dict):
            detection_result = raw

        if not detection_result:
            report = getattr(job, "silence_detection_report", None)
            if isinstance(report, dict) and report:
                inner = report.get("detection_result")
                if inner:
                    detection_result = inner

        if profile is None:
            job_profile = getattr(job, "profile_metadata", None)
            if isinstance(job_profile, dict):
                profile = job_profile

        return build_silence_classifier_run_report(
            detection_result=detection_result,
            contexts=contexts,
            profile=profile,
            metadata=metadata,
        )

    except Exception as exc:
        return SilenceClassifierRunReport(
            status="failed",
            errors=[f"silence_classifier_runner_failed: {exc}"],
            recommendation="retry_or_fix_detection_result",
            metadata=dict(metadata or {}),
        )
