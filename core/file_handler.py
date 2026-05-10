from __future__ import annotations

from pathlib import Path
from typing import Any

from core.file_acceptance import validate_file_info
from core.file_probe import probe_file
from core.file_readability import check_file_readability
from core.stream_classifier import classify_file_streams


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if hasattr(value, "to_dict"):
        return value.to_dict()

    if isinstance(value, dict):
        return dict(value)

    return {}


def _collect_warnings(*items: dict[str, Any]) -> list[str]:
    warnings: list[str] = []

    for item in items:
        for warning in item.get("warnings", []) or []:
            if warning not in warnings:
                warnings.append(warning)

    return warnings


def _collect_errors(*items: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for item in items:
        for error in item.get("errors", []) or []:
            if error not in errors:
                errors.append(error)

    return errors


def build_file_handler_report(
    path: str | Path,
    profile: dict[str, Any] | None = None,
    readability_seconds: float = 3.0,
) -> dict[str, Any]:
    file_info = probe_file(path)
    file_acceptance = validate_file_info(file_info, profile=profile)
    stream_classification = classify_file_streams(file_info)

    readability = None
    if file_acceptance.accepted:
        readability = check_file_readability(
            path,
            seconds=readability_seconds,
        )

    file_info_dict = _to_dict(file_info)
    acceptance_dict = _to_dict(file_acceptance)
    stream_dict = _to_dict(stream_classification)
    readability_dict = _to_dict(readability)

    warnings = _collect_warnings(
        acceptance_dict,
        stream_dict,
        readability_dict,
    )
    errors = _collect_errors(
        acceptance_dict,
        readability_dict,
    )

    accepted = bool(acceptance_dict.get("accepted", False))
    readable = bool(readability_dict.get("readable", False)) if readability_dict else False

    needs_manual_review = bool(stream_dict.get("needs_manual_review", False))
    if readability_dict.get("recommendation") == "manual_review":
        needs_manual_review = True

    if not accepted:
        status = "rejected"
        recommendation = "reject"
    elif accepted and not readable:
        status = "unreadable"
        recommendation = "reject"
    elif needs_manual_review or warnings:
        status = "accepted_with_review"
        recommendation = "accept_with_review"
    else:
        status = "accepted"
        recommendation = "accept"

    return {
        "file_info": file_info_dict,
        "file_acceptance": acceptance_dict,
        "stream_classification": stream_dict,
        "file_readability": readability_dict,
        "accepted": accepted,
        "readable": readable,
        "needs_manual_review": needs_manual_review,
        "status": status,
        "warnings": warnings,
        "errors": errors,
        "recommendation": recommendation,
    }


def apply_file_handler_report_to_job(job: Any, report: dict[str, Any]) -> Any:
    job.file_info = dict(report.get("file_info") or {})
    job.file_acceptance = dict(report.get("file_acceptance") or {})
    job.stream_classification = dict(report.get("stream_classification") or {})
    job.file_readability = dict(report.get("file_readability") or {})
    job.file_handler_report = dict(report)

    if hasattr(job, "touch"):
        job.touch()

    return job


def run_file_handler_for_job(
    job: Any,
    input_path: str | Path,
    profile: dict[str, Any] | None = None,
    readability_seconds: float = 3.0,
) -> dict[str, Any]:
    report = build_file_handler_report(
        path=input_path,
        profile=profile,
        readability_seconds=readability_seconds,
    )
    apply_file_handler_report_to_job(job, report)
    return report
