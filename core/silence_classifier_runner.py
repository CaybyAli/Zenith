from __future__ import annotations

from typing import Any

from core.adaptive_silence_classifier import classify_silence_detection_result
from core.silence_context_builder import build_silence_contexts_from_detection_result
from models.silence_classifier_run import SilenceClassifierRunReport


def build_silence_classifier_run_report(
    detection_result: Any,
    contexts: list[dict[str, Any]] | None = None,
    profile: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    energy_timeline: list[dict[str, Any]] | None = None,
    content_timeline: list[dict[str, Any]] | None = None,
    speech_segments: list[dict[str, Any]] | None = None,
    auto_build_contexts: bool = True,
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

        context_build_status: str | None = None
        context_build_result: dict[str, Any] = {}
        resolved_contexts: list[dict[str, Any]] = []
        context_count: int = 0
        high_energy_context_count: int = 0
        context_warnings: list[str] = []
        context_errors: list[str] = []

        if contexts is not None:
            resolved_contexts = list(contexts)
            context_build_status = "provided"
            context_count = len(resolved_contexts)
        elif auto_build_contexts:
            try:
                ctx_result = build_silence_contexts_from_detection_result(
                    detection_result,
                    energy_timeline=energy_timeline,
                    content_timeline=content_timeline,
                    speech_segments=speech_segments,
                )
                context_build_status = ctx_result.status
                context_build_result = ctx_result.to_dict()
                resolved_contexts = [ctx.to_dict() for ctx in ctx_result.contexts]
                context_count = ctx_result.context_count
                high_energy_context_count = ctx_result.high_energy_context_count
                context_warnings = list(ctx_result.warnings)
                context_errors = list(ctx_result.errors)
            except Exception as exc:
                context_build_status = "failed"
                context_warnings.append(f"context_build_failed: {exc}")
        else:
            context_build_status = "disabled"

        classifier_contexts = resolved_contexts if resolved_contexts else None

        classification_result = classify_silence_detection_result(
            detection_result,
            contexts=classifier_contexts,
            profile=profile,
        )

        classification_result_dict = classification_result.to_dict()
        classifications = [c.to_dict() for c in classification_result.classifications]

        errors = list(classification_result.errors) + context_errors
        warnings = list(classification_result.warnings) + context_warnings

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
            context_build_status=context_build_status,
            context_build_result=context_build_result,
            contexts=resolved_contexts,
            context_count=context_count,
            high_energy_context_count=high_energy_context_count,
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
    energy_timeline: list[dict[str, Any]] | None = None,
    content_timeline: list[dict[str, Any]] | None = None,
    speech_segments: list[dict[str, Any]] | None = None,
    auto_build_contexts: bool = True,
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

        if energy_timeline is None:
            job_energy = getattr(job, "energy_timeline", None)
            if isinstance(job_energy, list):
                energy_timeline = job_energy

        if content_timeline is None:
            job_content = getattr(job, "content_timeline", None)
            if isinstance(job_content, list):
                content_timeline = job_content

        if speech_segments is None:
            job_speech = getattr(job, "speech_segments", None)
            if isinstance(job_speech, list):
                speech_segments = job_speech
            else:
                job_transcript = getattr(job, "transcript_segments", None)
                if isinstance(job_transcript, list):
                    speech_segments = job_transcript

        return build_silence_classifier_run_report(
            detection_result=detection_result,
            contexts=contexts,
            profile=profile,
            metadata=metadata,
            energy_timeline=energy_timeline,
            content_timeline=content_timeline,
            speech_segments=speech_segments,
            auto_build_contexts=auto_build_contexts,
        )

    except Exception as exc:
        return SilenceClassifierRunReport(
            status="failed",
            errors=[f"silence_classifier_runner_failed: {exc}"],
            recommendation="retry_or_fix_detection_result",
            metadata=dict(metadata or {}),
        )
