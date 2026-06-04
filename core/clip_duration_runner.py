from __future__ import annotations

from typing import Any

from core.clip_duration_optimizer import optimize_clip_durations
from core.style_dna_pacing_adapter import StyleDnaPacingAdapter
from models.clip_duration import ClipDurationOptimizationPlan
from models.clip_duration_run import ClipDurationRunReport


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


def _build_duration_profile_from_style_dna_decision(decision: Any) -> dict[str, Any] | None:
    if not bool(getattr(decision, "loaded", False)):
        return None

    target_clip_seconds = getattr(decision, "target_clip_seconds", None)
    confidence = getattr(decision, "confidence", 0.0)

    try:
        target_clip_seconds = float(target_clip_seconds)
        confidence = float(confidence)
    except (TypeError, ValueError):
        return None

    if target_clip_seconds <= 0.0 or confidence <= 0.0:
        return None

    target_rule = {"target": target_clip_seconds}
    return {
        "duration_rules": {
            "KEEP": dict(target_rule),
            "REVIEW_KEEP": dict(target_rule),
            "REVIEW_TRIM": dict(target_rule),
            "UNKNOWN_REVIEW": dict(target_rule),
        }
    }


def _merge_duration_profile(
    existing_profile: Any,
    style_profile: dict[str, Any],
) -> dict[str, Any]:
    profile = dict(existing_profile) if isinstance(existing_profile, dict) else {}

    existing_rules = profile.get("duration_rules")
    merged_rules = dict(existing_rules) if isinstance(existing_rules, dict) else {}

    style_rules = style_profile.get("duration_rules")
    if isinstance(style_rules, dict):
        for action, rule in style_rules.items():
            base_rule = merged_rules.get(action)
            merged_rule = dict(base_rule) if isinstance(base_rule, dict) else {}
            if isinstance(rule, dict):
                merged_rule.update(rule)
            merged_rules[action] = merged_rule

    profile["duration_rules"] = merged_rules
    return profile


def _apply_style_dna_pacing_metadata(run_metadata: dict[str, Any]) -> dict[str, Any]:
    enriched_metadata = dict(run_metadata or {})

    if enriched_metadata.get("style_dna_pacing_enabled") is not True:
        return enriched_metadata

    try:
        style_dna_path = enriched_metadata.get("style_dna_path")
        adapter = StyleDnaPacingAdapter()
        if style_dna_path:
            decision = adapter.load_decision(style_dna_path)
        else:
            decision = adapter.load_decision()

        enriched_metadata["style_dna_pacing_decision"] = decision.to_dict()

        style_profile = _build_duration_profile_from_style_dna_decision(decision)
        if style_profile:
            enriched_metadata["profile"] = _merge_duration_profile(
                enriched_metadata.get("profile"),
                style_profile,
            )
            enriched_metadata["style_dna_pacing_profile_applied"] = True
        else:
            enriched_metadata["style_dna_pacing_profile_applied"] = False

    except Exception as exc:
        enriched_metadata["style_dna_pacing_profile_applied"] = False
        enriched_metadata["style_dna_pacing_error"] = str(exc)

    return enriched_metadata


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

    nested_plan = data.get("cut_list_plan")
    if nested_plan is not None:
        nested_data = _object_to_dict(nested_plan)
        for key in keys:
            value = nested_data.get(key)
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


def _read_cut_list_items_from_job(job: Any) -> list[Any]:
    direct_items = _extract_list_from_container(
        _get_job_value(job, "cut_list_items"),
        (
            "items",
            "cut_list_items",
            "recommendations",
            "results",
        ),
    )
    if direct_items:
        return direct_items

    report_items = _extract_list_from_container(
        _get_job_value(job, "cut_list_report"),
        (
            "items",
            "cut_list_items",
            "recommendations",
            "results",
        ),
    )
    if report_items:
        return report_items

    return []


def _build_report_from_plan(
    plan: ClipDurationOptimizationPlan,
    metadata: dict[str, Any] | None = None,
) -> ClipDurationRunReport:
    return ClipDurationRunReport(
        status=plan.status,
        source="clip_duration_optimizer",
        clip_duration_plan=plan,
        recommendations=list(plan.recommendations),
        recommendation_count=plan.recommendation_count,
        duration_ok_count=plan.duration_ok_count,
        too_short_count=plan.too_short_count,
        too_long_count=plan.too_long_count,
        trim_review_count=plan.trim_review_count,
        extend_review_count=plan.extend_review_count,
        protect_duration_count=plan.protect_duration_count,
        censor_keep_count=plan.censor_keep_count,
        technical_review_count=plan.technical_review_count,
        invalid_timing_count=plan.invalid_timing_count,
        recommendation=plan.recommendation,
        warnings=list(plan.warnings or []),
        errors=list(plan.errors or []),
        metadata={
            **dict(plan.metadata or {}),
            **dict(metadata or {}),
        },
    )


def run_clip_duration_optimization_for_job(
    job: Any,
    metadata: dict[str, Any] | None = None,
) -> ClipDurationRunReport:
    run_metadata = dict(metadata or {})
    run_metadata = _apply_style_dna_pacing_metadata(run_metadata)
    cut_list_items = _read_cut_list_items_from_job(job)

    if not cut_list_items:
        plan = optimize_clip_durations(
            cut_list_items=[],
            metadata=run_metadata,
        )
        report = _build_report_from_plan(plan, metadata=run_metadata)
        report.status = "skipped_no_cut_list_items"
        report.recommendation = "clip_duration_skipped_no_cut_list_items"
        return report

    try:
        plan = optimize_clip_durations(
            cut_list_items=cut_list_items,
            metadata=run_metadata,
        )
        return _build_report_from_plan(plan, metadata=run_metadata)
    except Exception as exc:
        return ClipDurationRunReport(
            status="failed",
            source="clip_duration_optimizer",
            clip_duration_plan=None,
            recommendations=[],
            recommendation_count=0,
            recommendation="clip_duration_optimization_failed",
            warnings=[],
            errors=[str(exc)],
            metadata=run_metadata,
        )


def apply_clip_duration_run_report_to_job(
    job: Any,
    report: ClipDurationRunReport | dict[str, Any],
) -> Any:
    if isinstance(report, dict):
        report = ClipDurationRunReport.from_dict(report)

    report_dict = report.to_dict()
    recommendation_dicts = [
        recommendation.to_dict()
        for recommendation in report.recommendations
    ]

    _set_job_value(job, "clip_duration_report", report_dict)
    _set_job_value(job, "clip_duration_status", report.status)
    _set_job_value(job, "clip_duration_recommendations", recommendation_dicts)
    _set_job_value(job, "clip_duration_recommendation_count", report.recommendation_count)
    _set_job_value(job, "clip_duration_ok_count", report.duration_ok_count)
    _set_job_value(job, "clip_duration_too_short_count", report.too_short_count)
    _set_job_value(job, "clip_duration_too_long_count", report.too_long_count)
    _set_job_value(job, "clip_duration_trim_review_count", report.trim_review_count)
    _set_job_value(job, "clip_duration_extend_review_count", report.extend_review_count)
    _set_job_value(job, "clip_duration_protect_duration_count", report.protect_duration_count)
    _set_job_value(job, "clip_duration_censor_keep_count", report.censor_keep_count)
    _set_job_value(job, "clip_duration_technical_review_count", report.technical_review_count)
    _set_job_value(job, "clip_duration_invalid_timing_count", report.invalid_timing_count)
    _set_job_value(job, "clip_duration_recommendation", report.recommendation)

    return job
