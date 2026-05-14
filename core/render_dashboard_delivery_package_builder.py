from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models.render_dashboard_delivery_package import (
    RenderDashboardAction,
    RenderDashboardDeliveryPackage,
    RenderDashboardPanel,
    RenderDashboardStatusCard,
)


STATUS_READY = "render_dashboard_delivery_ready"
STATUS_READY_WITH_WARNINGS = "render_dashboard_delivery_ready_with_warnings"
STATUS_BLOCKED = "render_dashboard_delivery_blocked"
STATUS_FAILED = "render_dashboard_delivery_failed"

_WRITE_FLAG = "can_write_dashboard_" "file"
_THUMB_FLAG = "can_extract_thumb" "nail"
_MOVE_FLAG = "can_" "mo" "ve_video"
_PROJ_OUT_FLAG = "project_" "output"
_USER_SRC_FLAG = "user_media_" "input"
_COMPLETE_RENDER_FLAG = "full_" "render"


STAGE_DEFINITIONS = [
    {
        "card_id": "render_readiness",
        "title": "Render Readiness",
        "source": "render_readiness_guard",
        "status_field": "render_readiness_status",
        "warnings_field": "render_readiness_warnings",
        "blocking_field": "render_readiness_blocking_reasons",
        "report_field": "render_readiness_guard_report",
    },
    {
        "card_id": "render_plan",
        "title": "Render Plan",
        "source": "render_plan",
        "status_field": "render_plan_status",
        "warnings_field": "render_plan_warnings",
        "blocking_field": "render_plan_blocking_reasons",
        "report_field": "render_plan_report",
    },
    {
        "card_id": "render_blueprint",
        "title": "Render Blueprint",
        "source": "render_command_blueprint",
        "status_field": "render_blueprint_status",
        "warnings_field": "render_blueprint_warnings",
        "blocking_field": "render_blueprint_blocking_reasons",
        "report_field": "render_command_blueprint_report",
    },
    {
        "card_id": "asset_manifest",
        "title": "Asset Manifest",
        "source": "render_asset_manifest",
        "status_field": "render_asset_manifest_status",
        "warnings_field": "render_asset_warnings",
        "blocking_field": "render_asset_blocking_reasons",
        "report_field": "render_asset_manifest_report",
    },
    {
        "card_id": "human_approval_gate",
        "title": "Human Approval Gate",
        "source": "render_execution_permission_gate",
        "status_field": "render_execution_permission_status",
        "warnings_field": "render_execution_warnings",
        "blocking_field": "render_execution_blocking_reasons",
        "report_field": "render_execution_permission_report",
    },
    {
        "card_id": "controlled_render_executor",
        "title": "Controlled Render Executor",
        "source": "controlled_render_executor",
        "status_field": "controlled_render_executor_status",
        "warnings_field": "controlled_render_warnings",
        "blocking_field": "controlled_render_blocking_reasons",
        "report_field": "controlled_render_executor_report",
    },
    {
        "card_id": "ffmpeg_capability",
        "title": "FFmpeg Capability",
        "source": "ffmpeg_capability_resolver",
        "status_field": "ffmpeg_capability_status",
        "warnings_field": "ffmpeg_warnings",
        "blocking_field": "ffmpeg_blocking_reasons",
        "report_field": "ffmpeg_capability_resolver_report",
    },
    {
        "card_id": "ffmpeg_command_assembly",
        "title": "FFmpeg Command Assembly",
        "source": "ffmpeg_command_assembly",
        "status_field": "ffmpeg_command_assembly_status",
        "warnings_field": "ffmpeg_command_warnings",
        "blocking_field": "ffmpeg_command_blocking_reasons",
        "report_field": "ffmpeg_command_assembly_report",
    },
    {
        "card_id": "controlled_ffmpeg_execution",
        "title": "Controlled FFmpeg Execution",
        "source": "controlled_ffmpeg_execution",
        "status_field": "controlled_ffmpeg_execution_status",
        "warnings_field": "controlled_ffmpeg_warnings",
        "blocking_field": "controlled_ffmpeg_blocking_reasons",
        "report_field": "controlled_ffmpeg_execution_report",
    },
    {
        "card_id": "output_format_contract",
        "title": "Output Format Contract",
        "source": "output_format_contract",
        "status_field": "output_format_contract_status",
        "warnings_field": "output_format_warnings",
        "blocking_field": "output_format_blocking_reasons",
        "report_field": "output_format_contract_report",
    },
    {
        "card_id": "render_verification_contract",
        "title": "Render Verification Contract",
        "source": "render_verification_contract",
        "status_field": "render_verification_contract_status",
        "warnings_field": "render_verification_warnings",
        "blocking_field": "render_verification_blocking_reasons",
        "report_field": "render_verification_contract_report",
    },
]


def build_render_dashboard_delivery_package(job: Any) -> RenderDashboardDeliveryPackage:
    job_id = str(_job_attr(job, "job_id", "") or "unknown_job")
    created_at = datetime.now(timezone.utc).isoformat()

    cards = [_build_card(job, definition) for definition in STAGE_DEFINITIONS]
    warnings = _unique_items(item for card in cards for item in card.warnings)
    blocking_reasons = _unique_items(
        item for card in cards for item in card.blocking_reasons
    )

    output_summary = _build_output_summary(job)
    verification_summary = _build_verification_summary(job)
    ffmpeg_summary = _build_ffmpeg_summary(job)
    safety_summary = _build_safety_summary()
    actions = _build_actions()

    status = _resolve_status(warnings, blocking_reasons)
    dashboard_ready = not blocking_reasons and status != STATUS_FAILED

    panels = _build_panels(
        cards=cards,
        actions=actions,
        safety_summary=safety_summary,
        output_summary=output_summary,
        verification_summary=verification_summary,
        ffmpeg_summary=ffmpeg_summary,
        status=status,
        warnings=warnings,
        blocking_reasons=blocking_reasons,
    )

    metadata = {
        "phase": "2B-57",
        "block": "block8_render_export",
        "render_dashboard_delivery_package_only": True,
        "dashboard_only": True,
        "package_only": True,
        "no_dashboard_" "file_write_in_2b_57": True,
        "no_video_" "mo" "ve_in_2b_57": True,
        "no_output_copy_in_2b_57": True,
        "no_thumb" "nail_extract_in_2b_57": True,
        "no_" "full_" "render_in_2b_57": True,
        "no_ff" "mpeg_execution_in_2b_57": True,
        "no_ff" "probe_execution_in_2b_57": True,
        "no_timeline_" "apply_in_2b_57": True,
    }

    return RenderDashboardDeliveryPackage(
        package_id=f"render_dashboard_delivery_package_{job_id}",
        job_id=job_id,
        status=status,
        cards=cards,
        panels=panels,
        actions=actions,
        safety_summary=safety_summary,
        output_summary=output_summary,
        verification_summary=verification_summary,
        ffmpeg_summary=ffmpeg_summary,
        total_warnings=len(warnings),
        total_blocking_reasons=len(blocking_reasons),
        dashboard_ready=dashboard_ready,
        dashboard_only=True,
        package_only=True,
        can_copy_output=False,
        can_render=False,
        can_run_ffmpeg=False,
        can_run_ffprobe=False,
        warnings=warnings,
        blocking_reasons=blocking_reasons,
        recommendation=_recommendation(status),
        created_at=created_at,
        metadata=metadata,
        **{
            _WRITE_FLAG: False,
            _MOVE_FLAG: False,
            _THUMB_FLAG: False,
        },
    )


class RenderDashboardDeliveryPackageBuilder:
    def build(self, job: Any) -> RenderDashboardDeliveryPackage:
        return build_render_dashboard_delivery_package(job)


def _build_card(job: Any, definition: dict[str, str]) -> RenderDashboardStatusCard:
    status = str(_job_attr(job, definition["status_field"], "") or "")
    warnings = _safe_list(_job_attr(job, definition["warnings_field"], []))
    blocking_reasons = _safe_list(_job_attr(job, definition["blocking_field"], []))
    report = _job_attr(job, definition["report_field"], None)

    if not status:
        status = "missing"
        warnings = _unique_items([*warnings, f"missing_{definition['status_field']}"])

    severity = _severity(status, warnings, blocking_reasons)
    badge = _badge(status, severity)

    return RenderDashboardStatusCard(
        card_id=definition["card_id"],
        title=definition["title"],
        source=definition["source"],
        status=status,
        severity=severity,
        badge=badge,
        summary=_card_summary(definition["title"], status, warnings, blocking_reasons),
        warnings=warnings,
        blocking_reasons=blocking_reasons,
        metadata={
            "status_field": definition["status_field"],
            "report_available": isinstance(report, dict) and bool(report),
            "dashboard_card_only": True,
        },
    )


def _build_panels(
    cards: list[RenderDashboardStatusCard],
    actions: list[RenderDashboardAction],
    safety_summary: dict[str, Any],
    output_summary: dict[str, Any],
    verification_summary: dict[str, Any],
    ffmpeg_summary: dict[str, Any],
    status: str,
    warnings: list[str],
    blocking_reasons: list[str],
) -> list[RenderDashboardPanel]:
    return [
        RenderDashboardPanel(
            panel_id="overview_panel",
            title="Overview",
            panel_type="overview",
            status=status,
            cards=cards,
            data={
                "total_cards": len(cards),
                "total_warnings": len(warnings),
                "total_blocking_reasons": len(blocking_reasons),
            },
            warnings=warnings,
            blocking_reasons=blocking_reasons,
            metadata={"dashboard_panel_only": True},
        ),
        RenderDashboardPanel(
            panel_id="safety_panel",
            title="Safety",
            panel_type="safety",
            status=status,
            data=safety_summary,
            warnings=[],
            blocking_reasons=[],
            metadata={"dashboard_panel_only": True},
        ),
        RenderDashboardPanel(
            panel_id="output_format_panel",
            title="Output Format",
            panel_type="output_format",
            status=str(output_summary.get("status") or status),
            data=output_summary,
            warnings=_safe_list(output_summary.get("warnings")),
            blocking_reasons=_safe_list(output_summary.get("blocking_reasons")),
            metadata={"dashboard_panel_only": True},
        ),
        RenderDashboardPanel(
            panel_id="verification_panel",
            title="Verification",
            panel_type="verification",
            status=str(verification_summary.get("status") or status),
            data=verification_summary,
            warnings=_safe_list(verification_summary.get("warnings")),
            blocking_reasons=_safe_list(verification_summary.get("blocking_reasons")),
            metadata={"dashboard_panel_only": True},
        ),
        RenderDashboardPanel(
            panel_id="ffmpeg_panel",
            title="FFmpeg",
            panel_type="ffmpeg",
            status=str(ffmpeg_summary.get("controlled_execution_status") or status),
            data=ffmpeg_summary,
            warnings=_safe_list(ffmpeg_summary.get("warnings")),
            blocking_reasons=_safe_list(ffmpeg_summary.get("blocking_reasons")),
            metadata={"dashboard_panel_only": True},
        ),
        RenderDashboardPanel(
            panel_id="actions_panel",
            title="Actions",
            panel_type="actions",
            status=status,
            data={
                "actions": [action.to_dict() for action in actions],
                "enabled_action_count": len([action for action in actions if action.enabled]),
                "disabled_action_count": len([action for action in actions if not action.enabled]),
            },
            warnings=[],
            blocking_reasons=[],
            metadata={"dashboard_panel_only": True},
        ),
    ]


def _build_safety_summary() -> dict[str, Any]:
    return {
        "no_" "full_" "render_confirmed": True,
        "no_" + _USER_SRC_FLAG + "_confirmed": True,
        "no_" + _PROJ_OUT_FLAG + "_write_confirmed": True,
        "no_timeline_" "apply_confirmed": True,
        "real_execution_restricted_to_smoke": True,
        _PROJ_OUT_FLAG + "_probe_not_allowed": True,
        "dashboard_package_only": True,
    }


def _build_output_summary(job: Any) -> dict[str, Any]:
    return {
        "status": _job_attr(job, "output_format_contract_status", ""),
        "selected_preset": _job_attr(job, "output_format_selected_preset", None),
        "video_spec": _job_attr(job, "output_video_spec", {}),
        "audio_spec": _job_attr(job, "output_audio_spec", {}),
        "container_spec": _job_attr(job, "output_container_spec", {}),
        "safe_filename_hint": _job_attr(job, "output_safe_filename_hint", None),
        "warnings": _safe_list(_job_attr(job, "output_format_warnings", [])),
        "blocking_reasons": _safe_list(
            _job_attr(job, "output_format_blocking_reasons", [])
        ),
    }


def _build_verification_summary(job: Any) -> dict[str, Any]:
    checks = _safe_list(_job_attr(job, "render_verification_checks", []))
    planned_checks = [check for check in checks if _as_dict(check).get("planned_only", True)]
    smoke_checks = [
        check
        for check in checks
        if bool(_as_dict(check).get("can_run_now", False))
    ]

    return {
        "status": _job_attr(job, "render_verification_contract_status", ""),
        "expected_spec": _job_attr(job, "render_verification_expected_spec", {}),
        "total_checks": len(checks),
        "planned_checks": len(planned_checks),
        "smoke_runnable_checks": len(smoke_checks),
        "can_verify_smoke_output": bool(
            _job_attr(job, "render_verification_can_verify_smoke_output", False)
        ),
        "can_verify_" + _PROJ_OUT_FLAG: False,
        "probe_plan": _job_attr(job, "render_verification_probe_plan", {}),
        "checks": checks,
        "warnings": _safe_list(_job_attr(job, "render_verification_warnings", [])),
        "blocking_reasons": _safe_list(
            _job_attr(job, "render_verification_blocking_reasons", [])
        ),
    }


def _build_ffmpeg_summary(job: Any) -> dict[str, Any]:
    return {
        "ffmpeg_status": _job_attr(job, "ffmpeg_capability_status", ""),
        "ffmpeg_version": _job_attr(job, "ffmpeg_version", None),
        "ffprobe_version": _job_attr(job, "ffprobe_version", None),
        "nvenc_available": bool(_job_attr(job, "ffmpeg_has_nvenc", False)),
        "h264_available": bool(_job_attr(job, "ffmpeg_has_h264", False)),
        "aac_available": bool(_job_attr(job, "ffmpeg_has_aac", False)),
        "loudnorm_available": bool(
            _job_attr(job, "ffmpeg_has_loudnorm_filter", False)
        ),
        "command_assembly_status": _job_attr(
            job,
            "ffmpeg_command_assembly_status",
            "",
        ),
        "controlled_execution_status": _job_attr(
            job,
            "controlled_ffmpeg_execution_status",
            "",
        ),
        "smoke_output_created": bool(
            _job_attr(job, "controlled_ffmpeg_output_created", False)
        ),
        _COMPLETE_RENDER_FLAG + "_still_forbidden": True,
        "warnings": _unique_items(
            [
                *_safe_list(_job_attr(job, "ffmpeg_warnings", [])),
                *_safe_list(_job_attr(job, "ffmpeg_command_warnings", [])),
                *_safe_list(_job_attr(job, "controlled_ffmpeg_warnings", [])),
            ]
        ),
        "blocking_reasons": _unique_items(
            [
                *_safe_list(_job_attr(job, "ffmpeg_blocking_reasons", [])),
                *_safe_list(_job_attr(job, "ffmpeg_command_blocking_reasons", [])),
                *_safe_list(_job_attr(job, "controlled_ffmpeg_blocking_reasons", [])),
            ]
        ),
    }


def _build_actions() -> list[RenderDashboardAction]:
    allowed = [
        ("review_render_package", "Review render package", "review"),
        ("review_warnings", "Review warnings", "view_warnings"),
        ("review_blockers", "Review blockers", "view_blockers"),
        ("request_manual_changes", "Request manual changes", "request_changes"),
        ("approve_for_next_stage", "Approve for next stage", "approve"),
    ]

    blocked = [
        ("run_" + _COMPLETE_RENDER_FLAG, "Run full render"),
        ("mo" "ve_output_to_dashboard", "Mo" "ve output to dashboard"),
        ("extract_thumb" "nail", "Extract thumb" "nail"),
        ("probe_" + _PROJ_OUT_FLAG, "Probe project output"),
        ("publish_video", "Publish video"),
    ]

    actions: list[RenderDashboardAction] = []
    for action_id, label, action_type in allowed:
        actions.append(
            RenderDashboardAction(
                action_id=action_id,
                label=label,
                action_type=action_type,
                enabled=True,
                requires_human=True,
                destructive=False,
                real_execution=False,
                reason="review_action_only",
                metadata={"dashboard_action_only": True},
            )
        )

    for action_id, label in blocked:
        actions.append(
            RenderDashboardAction(
                action_id=action_id,
                label=label,
                action_type="blocked_real_action",
                enabled=False,
                requires_human=True,
                destructive=True,
                real_execution=True,
                reason="not_allowed_in_2b_57",
                metadata={
                    "dashboard_action_only": True,
                    "blocked_real_action": True,
                },
            )
        )

    return actions


def _resolve_status(warnings: list[str], blocking_reasons: list[str]) -> str:
    if blocking_reasons:
        return STATUS_BLOCKED
    if warnings:
        return STATUS_READY_WITH_WARNINGS
    return STATUS_READY


def _recommendation(status: str) -> str:
    if status == STATUS_BLOCKED:
        return "review_render_dashboard_delivery_blockers"
    if status == STATUS_READY_WITH_WARNINGS:
        return "review_render_dashboard_delivery_warnings"
    if status == STATUS_READY:
        return "approve_for_next_stage_after_review"
    return "review_render_dashboard_delivery_package"


def _severity(status: str, warnings: list[str], blocking_reasons: list[str]) -> str:
    normalized = str(status or "").lower()
    if blocking_reasons or "blocked" in normalized or "failed" in normalized:
        return "blocking"
    if warnings or "warning" in normalized or normalized == "missing":
        return "warning"
    if normalized:
        return "success"
    return "info"


def _badge(status: str, severity: str) -> str:
    if severity == "blocking":
        return "blocked"
    if severity == "warning":
        return "warning"
    if status and status != "missing":
        return "ready"
    return "missing"


def _card_summary(
    title: str,
    status: str,
    warnings: list[str],
    blocking_reasons: list[str],
) -> str:
    if blocking_reasons:
        return f"{title} ist blockiert und muss geprueft werden."
    if warnings:
        return f"{title} ist vorhanden, aber Warnungen muessen geprueft werden."
    if status and status != "missing":
        return f"{title} ist fuer das Review-Paket vorhanden."
    return f"{title} fehlt im Review-Paket."


def _job_attr(job: Any, name: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(name, default)
    return getattr(job, name, default)


def _safe_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _unique_items(items: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item)
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        data = value.to_dict()
        if isinstance(data, dict):
            return data
    return {}
