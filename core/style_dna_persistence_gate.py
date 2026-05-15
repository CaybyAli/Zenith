from __future__ import annotations

import hashlib
import json
from typing import Any

from models.style_dna_persistence_gate import (
    ALLOWED_REQUEST_STATUSES,
    PHASE_METADATA,
    REQUEST_STATUS_APPROVED_WRITE,
    REQUEST_STATUS_NEEDS_MANUAL_CHANGES,
    REQUEST_STATUS_PENDING_WRITE_REVIEW,
    REQUEST_STATUS_REJECTED_WRITE,
    STYLE_DNA_PERSISTENCE_STATUS_APPROVED_WRITE,
    STYLE_DNA_PERSISTENCE_STATUS_BLOCKED,
    STYLE_DNA_PERSISTENCE_STATUS_NEEDS_MANUAL_CHANGES,
    STYLE_DNA_PERSISTENCE_STATUS_PENDING_WRITE_REVIEW,
    STYLE_DNA_PERSISTENCE_STATUS_REJECTED_WRITE,
    StyleDNAPersistenceGate,
    StyleDNAPersistenceGateReport,
    StyleDNAPersistenceWriteIntent,
    utc_now_iso,
)


APPLY_STATUS_WAITING = "style_dna_apply_plan_waiting_for_review"
APPLY_STATUS_READY = "style_dna_apply_plan_ready"
APPLY_STATUS_READY_WITH_WARNINGS = "style_dna_apply_plan_ready_with_warnings"
APPLY_STATUS_BLOCKED = "style_dna_apply_plan_blocked"
APPLY_STATUS_FAILED = "style_dna_apply_plan_failed"

RECOMMENDATION_REVIEW_GATE = "review_style_dna_persistence_gate"
RECOMMENDATION_WAIT = "wait_for_final_style_dna_write_permission"
RECOMMENDATION_FIX_BLOCKERS = "resolve_style_dna_persistence_gate_blockers"

BLOCKING_APPLY_PLAN_STATUS_MISSING = "style_dna_apply_plan_status_missing"
BLOCKING_APPLY_PLAN_BLOCKED_OR_FAILED = "style_dna_apply_plan_blocked_or_failed"
BLOCKING_APPLY_PLAN_HAS_BLOCKERS = "style_dna_apply_plan_has_blocking_reasons"
BLOCKING_APPLY_PLAN_NOT_READY = "style_dna_apply_plan_not_ready_for_future_file_write"
BLOCKING_APPLY_PLAN_NO_OPERATIONS = "style_dna_apply_plan_has_no_operations"
BLOCKING_APPLY_PLAN_NO_APPROVED_OPERATIONS = "style_dna_apply_plan_has_no_approved_operations"
BLOCKING_APPLY_PLAN_UNSAFE_PERMISSION = "style_dna_apply_plan_contains_unsafe_permission"
BLOCKING_UNKNOWN_REQUEST_STATUS = "style_dna_persistence_requested_status_unknown"
BLOCKING_APPROVED_BY_REQUIRED = "style_dna_persistence_approved_by_required"
BLOCKING_AFTER_PREVIEW_REQUIRED = "style_dna_persistence_after_preview_required"
BLOCKING_BACKUP_REQUIRED = "style_dna_persistence_backup_required"
BLOCKING_TARGET_HINT_REQUIRED = "style_dna_persistence_target_path_hint_required"
BLOCKING_TARGET_HINT_URL = "style_dna_persistence_target_path_hint_url_not_allowed"
BLOCKING_TARGET_HINT_TRAVERSAL = "style_dna_persistence_target_path_hint_traversal_not_allowed"
BLOCKING_FILE_WRITE_REQUESTED = "style_dna_file_write_not_allowed_in_2b_63"

WARNING_FILE_WRITE_REQUEST_IGNORED = "style_dna_file_write_not_allowed_in_2b_63"
WARNING_TARGET_HINT_NOT_JSON = "style_dna_persistence_target_path_hint_should_end_with_json"
WARNING_APPROVED_BY_RECOMMENDED = "style_dna_persistence_approved_by_recommended"
WARNING_COMMENT_RECOMMENDED = "style_dna_persistence_comment_recommended"
WARNING_SOURCE_APPLY_PLAN_WAITING = "style_dna_apply_plan_waiting_for_review"

UNSAFE_APPLY_FLAGS = [
    "style_dna_apply_can_write_style_dna",
    "style_dna_apply_can_apply_style_dna",
    "style_dna_apply_can_update_profile",
    "style_dna_apply_can_change_cutting_rules",
    "style_dna_apply_can_modify_timeline",
    "style_dna_apply_can_trigger_render",
    "style_dna_apply_can_publish",
]


def build_style_dna_persistence_gate_report(job: Any) -> dict[str, Any]:
    job_id = _text(_get(job, "job_id") or _get(job, "id") or "unknown_job")
    profile = _resolve_profile(job)

    requested_status = _normalize_requested_status(
        _get(job, "style_dna_persistence_requested_status")
    )
    approved_by = _optional_text(_get(job, "style_dna_persistence_approved_by"))
    comment = _optional_text(_get(job, "style_dna_persistence_comment"))
    target_path_hint = _optional_text(
        _get(job, "style_dna_persistence_target_path_hint")
    )
    backup_required = bool(
        _get(job, "style_dna_persistence_backup_required", True)
    )
    allow_file_write = bool(
        _get(job, "style_dna_persistence_allow_file_write", False)
    )

    warnings: list[str] = []
    blocking_reasons: list[str] = []

    source_apply_plan = _dict(_get(job, "style_dna_apply_plan"))
    source_apply_plan_status = _text(_get(job, "style_dna_apply_plan_status"))
    source_apply_blocking_reasons = _text_list(
        _get(job, "style_dna_apply_blocking_reasons")
    )
    source_ready = bool(_get(job, "style_dna_apply_ready_for_future_file_write", False))
    source_operation_count = _int(_get(job, "style_dna_apply_operation_count"), 0)
    source_approved_operation_count = _int(
        _get(job, "style_dna_apply_approved_operation_count"),
        0,
    )
    source_before_snapshot = _dict(_get(job, "style_dna_apply_before_snapshot"))
    source_after_preview = _dict(_get(job, "style_dna_apply_after_preview"))

    if not source_apply_plan_status:
        blocking_reasons.append(BLOCKING_APPLY_PLAN_STATUS_MISSING)
    if source_apply_plan_status in {APPLY_STATUS_BLOCKED, APPLY_STATUS_FAILED}:
        blocking_reasons.append(BLOCKING_APPLY_PLAN_BLOCKED_OR_FAILED)
    if source_apply_blocking_reasons:
        blocking_reasons.append(BLOCKING_APPLY_PLAN_HAS_BLOCKERS)

    unsafe_flags = [
        flag for flag in UNSAFE_APPLY_FLAGS if bool(_get(job, flag, False))
    ]
    if unsafe_flags:
        blocking_reasons.append(BLOCKING_APPLY_PLAN_UNSAFE_PERMISSION)

    if allow_file_write:
        warnings.append(WARNING_FILE_WRITE_REQUEST_IGNORED)
        blocking_reasons.append(BLOCKING_FILE_WRITE_REQUESTED)

    if requested_status not in ALLOWED_REQUEST_STATUSES:
        blocking_reasons.append(BLOCKING_UNKNOWN_REQUEST_STATUS)

    if target_path_hint:
        _validate_target_path_hint(
            target_path_hint=target_path_hint,
            warnings=warnings,
            blocking_reasons=blocking_reasons,
        )

    source_waiting = source_apply_plan_status == APPLY_STATUS_WAITING
    source_ready_status = source_apply_plan_status in {
        APPLY_STATUS_READY,
        APPLY_STATUS_READY_WITH_WARNINGS,
    }

    if source_waiting:
        warnings.append(WARNING_SOURCE_APPLY_PLAN_WAITING)

    if requested_status == REQUEST_STATUS_PENDING_WRITE_REVIEW:
        if blocking_reasons:
            return _report(
                job_id=job_id,
                profile=profile,
                source_apply_plan=source_apply_plan,
                source_apply_plan_status=source_apply_plan_status,
                source_operation_count=source_operation_count,
                source_approved_operation_count=source_approved_operation_count,
                source_before_snapshot=source_before_snapshot,
                source_after_preview=source_after_preview,
                requested_status=requested_status,
                approved_by=approved_by,
                comment=comment,
                target_path_hint=target_path_hint,
                backup_required=backup_required,
                status=STYLE_DNA_PERSISTENCE_STATUS_BLOCKED,
                write_permission_ready_for_future=False,
                warnings=warnings,
                blocking_reasons=blocking_reasons,
                recommendation=RECOMMENDATION_FIX_BLOCKERS,
            )
        return _report(
            job_id=job_id,
            profile=profile,
            source_apply_plan=source_apply_plan,
            source_apply_plan_status=source_apply_plan_status,
            source_operation_count=source_operation_count,
            source_approved_operation_count=source_approved_operation_count,
            source_before_snapshot=source_before_snapshot,
            source_after_preview=source_after_preview,
            requested_status=requested_status,
            approved_by=approved_by,
            comment=comment,
            target_path_hint=target_path_hint,
            backup_required=backup_required,
            status=STYLE_DNA_PERSISTENCE_STATUS_PENDING_WRITE_REVIEW,
            write_permission_ready_for_future=False,
            warnings=warnings,
            blocking_reasons=[],
            recommendation=RECOMMENDATION_WAIT,
        )

    if not source_ready_status or not source_ready:
        blocking_reasons.append(BLOCKING_APPLY_PLAN_NOT_READY)
    if source_operation_count <= 0:
        blocking_reasons.append(BLOCKING_APPLY_PLAN_NO_OPERATIONS)
    if source_approved_operation_count <= 0:
        blocking_reasons.append(BLOCKING_APPLY_PLAN_NO_APPROVED_OPERATIONS)

    if requested_status == REQUEST_STATUS_APPROVED_WRITE:
        if not approved_by:
            blocking_reasons.append(BLOCKING_APPROVED_BY_REQUIRED)
        if not source_after_preview:
            blocking_reasons.append(BLOCKING_AFTER_PREVIEW_REQUIRED)
        if not backup_required:
            blocking_reasons.append(BLOCKING_BACKUP_REQUIRED)
        if not target_path_hint:
            blocking_reasons.append(BLOCKING_TARGET_HINT_REQUIRED)

        if blocking_reasons:
            return _report(
                job_id=job_id,
                profile=profile,
                source_apply_plan=source_apply_plan,
                source_apply_plan_status=source_apply_plan_status,
                source_operation_count=source_operation_count,
                source_approved_operation_count=source_approved_operation_count,
                source_before_snapshot=source_before_snapshot,
                source_after_preview=source_after_preview,
                requested_status=requested_status,
                approved_by=approved_by,
                comment=comment,
                target_path_hint=target_path_hint,
                backup_required=backup_required,
                status=STYLE_DNA_PERSISTENCE_STATUS_BLOCKED,
                write_permission_ready_for_future=False,
                warnings=warnings,
                blocking_reasons=blocking_reasons,
                recommendation=RECOMMENDATION_FIX_BLOCKERS,
            )

        return _report(
            job_id=job_id,
            profile=profile,
            source_apply_plan=source_apply_plan,
            source_apply_plan_status=source_apply_plan_status,
            source_operation_count=source_operation_count,
            source_approved_operation_count=source_approved_operation_count,
            source_before_snapshot=source_before_snapshot,
            source_after_preview=source_after_preview,
            requested_status=requested_status,
            approved_by=approved_by,
            comment=comment,
            target_path_hint=target_path_hint,
            backup_required=backup_required,
            status=STYLE_DNA_PERSISTENCE_STATUS_APPROVED_WRITE,
            write_permission_ready_for_future=True,
            warnings=warnings,
            blocking_reasons=[],
            recommendation=RECOMMENDATION_REVIEW_GATE,
        )

    if requested_status == REQUEST_STATUS_REJECTED_WRITE:
        if not approved_by:
            blocking_reasons.append(BLOCKING_APPROVED_BY_REQUIRED)

        if blocking_reasons:
            status = STYLE_DNA_PERSISTENCE_STATUS_BLOCKED
            recommendation = RECOMMENDATION_FIX_BLOCKERS
        else:
            status = STYLE_DNA_PERSISTENCE_STATUS_REJECTED_WRITE
            recommendation = RECOMMENDATION_REVIEW_GATE

        return _report(
            job_id=job_id,
            profile=profile,
            source_apply_plan=source_apply_plan,
            source_apply_plan_status=source_apply_plan_status,
            source_operation_count=source_operation_count,
            source_approved_operation_count=source_approved_operation_count,
            source_before_snapshot=source_before_snapshot,
            source_after_preview=source_after_preview,
            requested_status=requested_status,
            approved_by=approved_by,
            comment=comment,
            target_path_hint=target_path_hint,
            backup_required=backup_required,
            status=status,
            write_permission_ready_for_future=False,
            warnings=warnings,
            blocking_reasons=blocking_reasons,
            recommendation=recommendation,
        )

    if requested_status == REQUEST_STATUS_NEEDS_MANUAL_CHANGES:
        if not approved_by:
            warnings.append(WARNING_APPROVED_BY_RECOMMENDED)
        if not comment:
            warnings.append(WARNING_COMMENT_RECOMMENDED)

        if blocking_reasons:
            status = STYLE_DNA_PERSISTENCE_STATUS_BLOCKED
            recommendation = RECOMMENDATION_FIX_BLOCKERS
        else:
            status = STYLE_DNA_PERSISTENCE_STATUS_NEEDS_MANUAL_CHANGES
            recommendation = RECOMMENDATION_REVIEW_GATE

        return _report(
            job_id=job_id,
            profile=profile,
            source_apply_plan=source_apply_plan,
            source_apply_plan_status=source_apply_plan_status,
            source_operation_count=source_operation_count,
            source_approved_operation_count=source_approved_operation_count,
            source_before_snapshot=source_before_snapshot,
            source_after_preview=source_after_preview,
            requested_status=requested_status,
            approved_by=approved_by,
            comment=comment,
            target_path_hint=target_path_hint,
            backup_required=backup_required,
            status=status,
            write_permission_ready_for_future=False,
            warnings=warnings,
            blocking_reasons=blocking_reasons,
            recommendation=recommendation,
        )

    return _report(
        job_id=job_id,
        profile=profile,
        source_apply_plan=source_apply_plan,
        source_apply_plan_status=source_apply_plan_status,
        source_operation_count=source_operation_count,
        source_approved_operation_count=source_approved_operation_count,
        source_before_snapshot=source_before_snapshot,
        source_after_preview=source_after_preview,
        requested_status=requested_status,
        approved_by=approved_by,
        comment=comment,
        target_path_hint=target_path_hint,
        backup_required=backup_required,
        status=STYLE_DNA_PERSISTENCE_STATUS_BLOCKED,
        write_permission_ready_for_future=False,
        warnings=warnings,
        blocking_reasons=blocking_reasons or [BLOCKING_UNKNOWN_REQUEST_STATUS],
        recommendation=RECOMMENDATION_FIX_BLOCKERS,
    )


def _report(
    *,
    job_id: str,
    profile: str | None,
    source_apply_plan: dict[str, Any],
    source_apply_plan_status: str | None,
    source_operation_count: int,
    source_approved_operation_count: int,
    source_before_snapshot: dict[str, Any],
    source_after_preview: dict[str, Any],
    requested_status: str,
    approved_by: str | None,
    comment: str | None,
    target_path_hint: str | None,
    backup_required: bool,
    status: str,
    write_permission_ready_for_future: bool,
    warnings: list[str],
    blocking_reasons: list[str],
    recommendation: str,
) -> dict[str, Any]:
    clean_warnings = _unique(warnings)
    clean_blocking_reasons = _unique(blocking_reasons)
    source_apply_plan_id = _optional_text(source_apply_plan.get("plan_id"))

    write_preview_hash = _stable_hash(source_after_preview)

    write_intent = StyleDNAPersistenceWriteIntent(
        intent_id=f"{job_id}_style_dna_persistence_write_intent",
        profile=profile,
        target_path_hint=target_path_hint,
        operation_count=source_operation_count,
        approved_operation_count=source_approved_operation_count,
        backup_required=backup_required,
        before_snapshot=source_before_snapshot,
        after_preview=source_after_preview,
        write_preview_hash=write_preview_hash,
        planned_only=True,
        no_file_write_performed=True,
        warnings=clean_warnings,
        blocking_reasons=clean_blocking_reasons,
        metadata={
            **PHASE_METADATA,
            "source_apply_plan_id": source_apply_plan_id,
            "hash_algorithm": "sha256",
            "stable_json_sort_keys": True,
        },
    )

    gate = StyleDNAPersistenceGate(
        gate_id=f"{job_id}_style_dna_persistence_gate",
        job_id=job_id,
        source_apply_plan_id=source_apply_plan_id,
        requested_status=requested_status,
        status=status,
        approved_by=approved_by,
        comment=comment,
        write_intent=write_intent,
        write_permission_ready_for_future=bool(write_permission_ready_for_future),
        can_write_style_dna=False,
        can_apply_style_dna=False,
        can_update_profile=False,
        can_change_cutting_rules=False,
        can_modify_timeline=False,
        can_trigger_render=False,
        can_publish=False,
        warnings=clean_warnings,
        blocking_reasons=clean_blocking_reasons,
        recommendation=recommendation,
        created_at=utc_now_iso(),
        metadata={
            **PHASE_METADATA,
            "source_apply_plan_id": source_apply_plan_id,
            "source_apply_plan_status": source_apply_plan_status,
            "source_operation_count": source_operation_count,
            "source_approved_operation_count": source_approved_operation_count,
        },
    )

    report = StyleDNAPersistenceGateReport(
        report_id=f"{job_id}_style_dna_persistence_gate_report",
        job_id=job_id,
        status=status,
        gate=gate,
        source_apply_plan_status=source_apply_plan_status,
        source_operation_count=source_operation_count,
        write_permission_ready_for_future=bool(write_permission_ready_for_future),
        can_write_style_dna=False,
        can_apply_style_dna=False,
        can_update_profile=False,
        can_change_cutting_rules=False,
        can_modify_timeline=False,
        can_trigger_render=False,
        can_publish=False,
        warnings=clean_warnings,
        blocking_reasons=clean_blocking_reasons,
        recommendation=recommendation,
        created_at=utc_now_iso(),
        metadata={
            **PHASE_METADATA,
            "source_apply_plan_id": source_apply_plan_id,
            "requested_status": requested_status,
            "write_preview_hash": write_preview_hash,
        },
    )
    return report.to_dict()


def _validate_target_path_hint(
    *,
    target_path_hint: str,
    warnings: list[str],
    blocking_reasons: list[str],
) -> None:
    lowered = target_path_hint.lower()
    if lowered.startswith(("http://", "https://")):
        blocking_reasons.append(BLOCKING_TARGET_HINT_URL)
    if ".." in target_path_hint.replace("\\", "/").split("/"):
        blocking_reasons.append(BLOCKING_TARGET_HINT_TRAVERSAL)
    if not lowered.endswith(".json"):
        warnings.append(WARNING_TARGET_HINT_NOT_JSON)


def _stable_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_requested_status(value: Any) -> str:
    text = _text(value)
    return text or REQUEST_STATUS_PENDING_WRITE_REVIEW


def _resolve_profile(job: Any) -> str | None:
    explicit_profile = _text(_get(job, "style_dna_profile_name"))
    if explicit_profile:
        return explicit_profile

    apply_plan = _dict(_get(job, "style_dna_apply_plan"))
    profile = _text(apply_plan.get("profile") or _get(job, "profile"))
    return profile or None


def _get(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _optional_text(value: Any) -> str | None:
    text = _text(value)
    return text or None


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = _text(item)
        if text and text not in result:
            result.append(text)
    return result


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in result:
            result.append(text)
    return result
