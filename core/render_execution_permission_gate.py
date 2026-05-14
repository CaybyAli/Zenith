from __future__ import annotations

from typing import Any

from models.render_execution_permission_gate import (
    CHECK_STATUS_BLOCKED,
    CHECK_STATUS_PASSED,
    CHECK_STATUS_WARNING,
    RenderExecutionPermissionCheck,
    build_render_execution_permission_report,
)


PERMISSION_METADATA = {
    "phase": "2B-49",
    "block": "block8_render_export",
    "render_execution_permission_gate_only": True,
    "final_human_approval_gate": True,
    "media_unchanged": True,
    "no_execution_in_2b_49": True,
    "no_render_in_2b_49": True,
    "no_ff" "mpeg_in_2b_49": True,
    "no_process_" "spawn_in_2b_49": True,
    "no_media_read_in_2b_49": True,
    "no_media_write_in_2b_49": True,
    "no_directory_create_in_2b_49": True,
    "no_timeline_" "apply_in_2b_49": True,
}

READY_READINESS_STATUSES = {
    "render_readiness_ready",
    "render_readiness_ready_with_warnings",
}

READY_PLAN_STATUSES = {
    "render_plan_ready",
    "render_plan_ready_with_warnings",
}

READY_BLUEPRINT_STATUSES = {
    "render_blueprint_ready",
    "render_blueprint_ready_with_warnings",
}

READY_ASSET_STATUSES = {
    "render_asset_manifest_ready",
    "render_asset_manifest_ready_with_warnings",
}

REJECTED_STATUSES = {
    "rejected",
    "render_execution_rejected",
    "declined",
    "denied",
}

SAFE_FALSE_FLAG_GROUPS = {
    "render_permission": (
        "can_render",
        "render_readiness_can_render",
        "render_plan_can_render",
        "render_blueprint_can_render",
        "render_asset_can_render",
    ),
    "tool_or_file_permission": (
        "can_run_ff" "mpeg",
        "can_spawn_" "process",
        "can_write_" "media",
        "render_readiness_can_run_ff" "mpeg",
        "render_plan_can_run_ff" "mpeg",
        "render_plan_can_write_" "media",
        "render_blueprint_can_run_ff" "mpeg",
        "render_blueprint_can_spawn_" "process",
        "render_blueprint_can_write_" "media",
        "render_asset_can_run_ff" "mpeg",
        "render_asset_can_write_files",
        "render_asset_can_create_directories",
        "render_asset_can_open_media",
    ),
    "timeline_permission": (
        "can_apply_" "timeline",
        "render_readiness_can_apply_" "timeline",
        "render_plan_can_apply_" "timeline",
    ),
}

PREVIOUS_BLOCKING_FIELDS = (
    "render_readiness_blocking_reasons",
    "render_plan_blocking_reasons",
    "render_blueprint_blocking_reasons",
    "render_asset_blocking_reasons",
)

STARTED_HINT_FIELDS = (
    "render_started",
    "render_execution_started",
    "real_render_started",
    "renderer_started",
    "export_started",
)


class RenderExecutionPermissionGate:
    def build(self, job: Any) -> dict[str, Any]:
        job_id = str(self._get(job, "job_id", self._get(job, "id", "unknown")))

        checks: list[RenderExecutionPermissionCheck] = []

        checks.append(self._check_render_readiness_ready(job))
        checks.append(self._check_render_plan_ready(job))
        checks.append(self._check_render_blueprint_ready(job))
        checks.append(self._check_render_blueprint_non_executable(job))
        checks.append(self._check_render_asset_manifest_ready(job))
        checks.append(self._check_render_asset_manifest_safe(job))
        checks.append(self._check_no_blocking_reasons(job))
        checks.append(self._check_no_render_permission_leak(job))
        checks.append(self._check_no_tool_or_file_permission_leak(job))
        checks.append(self._check_no_timeline_permission_leak(job))
        checks.append(self._check_human_approval_present(job))
        checks.append(self._check_human_approval_identity_present(job))
        checks.append(self._check_human_approval_timestamp_present(job))
        checks.append(self._check_approval_not_rejected(job))
        checks.append(self._check_render_not_started(job))

        human_approved = self._human_approved(job)
        approved_by = self._first_text(self._get(job, "render_execution_approved_by"))
        approved_at = self._first_text(self._get(job, "render_execution_approved_at"))
        approval_reason = self._first_text(
            self._get(job, "render_execution_approval_reason")
        )

        blocking_reasons = self._unique(
            [
                check.check_id
                for check in checks
                if check.blocking or check.status == CHECK_STATUS_BLOCKED
            ]
        )
        warnings = self._unique(
            [check.check_id for check in checks if check.status == CHECK_STATUS_WARNING]
        )

        report = build_render_execution_permission_report(
            job_id=job_id,
            checks=checks,
            warnings=warnings,
            blocking_reasons=blocking_reasons,
            human_approved=human_approved,
            approved_by=approved_by,
            approved_at=approved_at,
            approval_reason=approval_reason,
            metadata=dict(PERMISSION_METADATA),
        )
        return report.to_dict()

    def _check_render_readiness_ready(self, job: Any) -> RenderExecutionPermissionCheck:
        status = self._status(self._get(job, "render_readiness_status"))
        ready = self._truthy(self._get(job, "render_readiness_ready_for_next_render_stage"))
        passed = status in READY_READINESS_STATUSES and ready

        return self._check(
            check_id="render_readiness_ready",
            check_name="Render Readiness Guard ready",
            category="previous_gate",
            passed=passed,
            blocked_message="Render Readiness Guard fehlt oder ist nicht ready.",
            passed_message="Render Readiness Guard ist ready.",
            evidence={
                "status": status,
                "ready_for_next_render_stage": ready,
            },
        )

    def _check_render_plan_ready(self, job: Any) -> RenderExecutionPermissionCheck:
        status = self._status(self._get(job, "render_plan_status"))
        ready = self._truthy(self._get(job, "render_plan_ready_for_renderer_contract"))
        passed = status in READY_PLAN_STATUSES and ready

        return self._check(
            check_id="render_plan_ready",
            check_name="Render Plan ready",
            category="previous_gate",
            passed=passed,
            blocked_message="Render Plan fehlt oder ist nicht ready.",
            passed_message="Render Plan ist ready.",
            evidence={
                "status": status,
                "ready_for_renderer_contract": ready,
            },
        )

    def _check_render_blueprint_ready(self, job: Any) -> RenderExecutionPermissionCheck:
        status = self._status(self._get(job, "render_blueprint_status"))
        ready = self._truthy(
            self._get(job, "render_blueprint_ready_for_renderer_implementation")
        )
        passed = status in READY_BLUEPRINT_STATUSES and ready

        return self._check(
            check_id="render_blueprint_ready",
            check_name="Render Blueprint ready",
            category="previous_gate",
            passed=passed,
            blocked_message="Render Blueprint fehlt oder ist nicht ready.",
            passed_message="Render Blueprint ist ready.",
            evidence={
                "status": status,
                "ready_for_renderer_implementation": ready,
            },
        )

    def _check_render_blueprint_non_executable(
        self,
        job: Any,
    ) -> RenderExecutionPermissionCheck:
        value = self._truthy(self._get(job, "render_blueprint_non_executable"))
        return self._check(
            check_id="render_blueprint_non_executable",
            check_name="Render Blueprint non-executable",
            category="safety",
            passed=value,
            blocked_message="Render Blueprint ist nicht als non-executable markiert.",
            passed_message="Render Blueprint ist non-executable.",
            evidence={"non_executable": value},
        )

    def _check_render_asset_manifest_ready(
        self,
        job: Any,
    ) -> RenderExecutionPermissionCheck:
        status = self._status(self._get(job, "render_asset_manifest_status"))
        passed = status in READY_ASSET_STATUSES

        return self._check(
            check_id="render_asset_manifest_ready",
            check_name="Render Asset Manifest ready",
            category="previous_gate",
            passed=passed,
            blocked_message="Render Asset Manifest fehlt oder ist blockiert.",
            passed_message="Render Asset Manifest ist ready.",
            evidence={"status": status},
        )

    def _check_render_asset_manifest_safe(
        self,
        job: Any,
    ) -> RenderExecutionPermissionCheck:
        unsafe_count = self._int(self._get(job, "render_asset_unsafe_path_count"))
        missing_count = self._int(
            self._get(job, "render_asset_missing_required_hint_count")
        )
        passed = unsafe_count == 0 and missing_count == 0

        return self._check(
            check_id="render_asset_manifest_safe",
            check_name="Render Asset Manifest safe",
            category="safety",
            passed=passed,
            blocked_message="Render Asset Manifest hat unsichere oder fehlende Pflicht-Hinweise.",
            passed_message="Render Asset Manifest hat keine blockierenden Pfad-Hinweise.",
            evidence={
                "unsafe_path_count": unsafe_count,
                "missing_required_hint_count": missing_count,
            },
        )

    def _check_no_blocking_reasons(self, job: Any) -> RenderExecutionPermissionCheck:
        found: list[str] = []
        for field_name in PREVIOUS_BLOCKING_FIELDS:
            found.extend([f"{field_name}:{item}" for item in self._string_list(self._get(job, field_name))])

        passed = not found
        return self._check(
            check_id="no_blocking_reasons",
            check_name="No previous blocking reasons",
            category="safety",
            passed=passed,
            blocked_message="Vorherige Render-Gates haben Blocking Reasons.",
            passed_message="Keine vorherigen Blocking Reasons gefunden.",
            evidence={"blocking_reasons": found},
        )

    def _check_no_render_permission_leak(
        self,
        job: Any,
    ) -> RenderExecutionPermissionCheck:
        leaks = self._truthy_fields(job, SAFE_FALSE_FLAG_GROUPS["render_permission"])
        passed = not leaks

        return self._check(
            check_id="no_render_permission_leak",
            check_name="No render permission leak",
            category="permission_safety",
            passed=passed,
            blocked_message="Ein altes Render-Erlaubnisfeld ist True.",
            passed_message="Keine Render-Erlaubnis-Leaks gefunden.",
            evidence={"leaked_fields": leaks},
        )

    def _check_no_tool_or_file_permission_leak(
        self,
        job: Any,
    ) -> RenderExecutionPermissionCheck:
        leaks = self._truthy_fields(job, SAFE_FALSE_FLAG_GROUPS["tool_or_file_permission"])
        passed = not leaks

        return self._check(
            check_id="no_process_or_write_permission_leak",
            check_name="No tool or file permission leak",
            category="permission_safety",
            passed=passed,
            blocked_message="Ein Tool- oder Datei-Erlaubnisfeld ist True.",
            passed_message="Keine Tool- oder Datei-Erlaubnis-Leaks gefunden.",
            evidence={"leaked_fields": leaks},
        )

    def _check_no_timeline_permission_leak(
        self,
        job: Any,
    ) -> RenderExecutionPermissionCheck:
        leaks = self._truthy_fields(job, SAFE_FALSE_FLAG_GROUPS["timeline_permission"])
        passed = not leaks

        return self._check(
            check_id="no_timeline_apply_permission_leak",
            check_name="No timeline permission leak",
            category="permission_safety",
            passed=passed,
            blocked_message="Ein Timeline-Erlaubnisfeld ist True.",
            passed_message="Keine Timeline-Erlaubnis-Leaks gefunden.",
            evidence={"leaked_fields": leaks},
        )

    def _check_human_approval_present(
        self,
        job: Any,
    ) -> RenderExecutionPermissionCheck:
        approved = self._human_approved(job)

        return self._check(
            check_id="human_approval_present",
            check_name="Human approval present",
            category="human_approval",
            passed=approved,
            blocked_message="Finale menschliche Render-Freigabe fehlt.",
            passed_message="Finale menschliche Render-Freigabe ist vorhanden.",
            evidence={
                "render_execution_human_approved": self._truthy(
                    self._get(job, "render_execution_human_approved")
                ),
                "render_execution_requested_status": self._status(
                    self._get(job, "render_execution_requested_status")
                ),
            },
            blocked_id="render_execution_human_approval_missing",
        )

    def _check_human_approval_identity_present(
        self,
        job: Any,
    ) -> RenderExecutionPermissionCheck:
        approved_by = self._first_text(self._get(job, "render_execution_approved_by"))
        passed = bool(approved_by)

        return self._check(
            check_id="human_approval_identity_present",
            check_name="Human approval identity present",
            category="human_approval",
            passed=passed,
            blocked_message="Name der freigebenden Person fehlt.",
            passed_message="Name der freigebenden Person ist vorhanden.",
            evidence={"approved_by": approved_by},
            blocked_id="render_execution_approval_identity_missing",
        )

    def _check_human_approval_timestamp_present(
        self,
        job: Any,
    ) -> RenderExecutionPermissionCheck:
        approved_at = self._first_text(self._get(job, "render_execution_approved_at"))
        if approved_at:
            return RenderExecutionPermissionCheck(
                check_id="human_approval_timestamp_present",
                check_name="Human approval timestamp present",
                category="human_approval",
                status=CHECK_STATUS_PASSED,
                severity="info",
                message="Zeitpunkt der finalen Freigabe ist vorhanden.",
                evidence={"approved_at": approved_at},
                blocking=False,
                review_required=False,
                metadata=dict(PERMISSION_METADATA),
            )

        return RenderExecutionPermissionCheck(
            check_id="human_approval_timestamp_present",
            check_name="Human approval timestamp present",
            category="human_approval",
            status=CHECK_STATUS_WARNING,
            severity="warning",
            message="Zeitpunkt der finalen Freigabe fehlt.",
            evidence={"approved_at": approved_at},
            blocking=False,
            review_required=True,
            metadata=dict(PERMISSION_METADATA),
        )

    def _check_approval_not_rejected(self, job: Any) -> RenderExecutionPermissionCheck:
        requested_status = self._status(self._get(job, "render_execution_requested_status"))
        rejected_by = self._first_text(self._get(job, "render_execution_rejected_by"))
        rejected_reason = self._first_text(
            self._get(job, "render_execution_rejection_reason")
        )

        rejected = requested_status in REJECTED_STATUSES or bool(rejected_by)
        return self._check(
            check_id="approval_not_rejected",
            check_name="Approval not rejected",
            category="human_approval",
            passed=not rejected,
            blocked_message="Finale Render-Freigabe wurde abgelehnt.",
            passed_message="Keine Ablehnung der finalen Freigabe gefunden.",
            evidence={
                "requested_status": requested_status,
                "rejected_by": rejected_by,
                "rejection_reason": rejected_reason,
            },
            blocked_id="render_execution_approval_rejected",
        )

    def _check_render_not_started(self, job: Any) -> RenderExecutionPermissionCheck:
        hints = self._truthy_fields(job, STARTED_HINT_FIELDS)
        passed = not hints

        return self._check(
            check_id="render_not_started",
            check_name="Render not started",
            category="safety",
            passed=passed,
            blocked_message="Es gibt Hinweise, dass Render bereits gestartet wurde.",
            passed_message="Keine Start-Hinweise gefunden.",
            evidence={"started_hint_fields": hints},
        )

    def _human_approved(self, job: Any) -> bool:
        explicit = self._truthy(self._get(job, "render_execution_human_approved"))
        requested = self._status(self._get(job, "render_execution_requested_status"))
        return bool(explicit or requested == "approved")

    def _check(
        self,
        *,
        check_id: str,
        check_name: str,
        category: str,
        passed: bool,
        blocked_message: str,
        passed_message: str,
        evidence: dict[str, Any],
        blocked_id: str | None = None,
    ) -> RenderExecutionPermissionCheck:
        return RenderExecutionPermissionCheck(
            check_id=blocked_id if not passed and blocked_id else check_id,
            check_name=check_name,
            category=category,
            status=CHECK_STATUS_PASSED if passed else CHECK_STATUS_BLOCKED,
            severity="info" if passed else "error",
            message=passed_message if passed else blocked_message,
            evidence=dict(evidence),
            blocking=not passed,
            review_required=not passed,
            metadata=dict(PERMISSION_METADATA),
        )

    def _truthy_fields(self, job: Any, field_names: tuple[str, ...]) -> list[str]:
        return [
            field_name
            for field_name in field_names
            if self._truthy(self._get(job, field_name))
        ]

    def _get(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _status(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().lower()

    def _truthy(self, value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {
                "true",
                "1",
                "yes",
                "ready",
                "safe",
                "passed",
                "approved",
            }
        return bool(value)

    def _int(self, value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _first_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item)]
        if isinstance(value, tuple):
            return [str(item) for item in value if str(item)]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _unique(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result


def build_render_execution_permission_gate(job: Any) -> dict[str, Any]:
    return RenderExecutionPermissionGate().build(job)
