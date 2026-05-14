from __future__ import annotations

from typing import Any

from models.render_readiness_guard import (
    CHECK_STATUS_BLOCKED,
    CHECK_STATUS_PASSED,
    CHECK_STATUS_WARNING,
    SEVERITY_BLOCKING,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    RenderReadinessCheck,
    RenderReadinessReport,
    build_report_from_checks,
)


BLOCK8_METADATA = {
    "phase": "2B-45",
    "block": "block8_render_export",
    "render_readiness_guard_only": True,
    "media_unchanged": True,
    "no_execution_in_2b_45": True,
    "no_render_in_2b_45": True,
    "no_ffmpeg_in_2b_45": True,
    "no_media_write_in_2b_45": True,
    "no_timeline_apply_in_2b_45": True,
}


READY_STATUSES = {
    "ready",
    "ready_with_warnings",
    "passed",
    "safe",
    "timeline_safety_passed",
    "timeline_safety_safe",
    "review_timeline_dashboard_ready",
    "review_timeline_dashboard_ready_with_warnings",
    "final_quality_ready",
    "final_quality_ready_with_warnings",
    "render_readiness_ready",
    "render_readiness_ready_with_warnings",
}

BLOCKED_STATUSES = {
    "blocked",
    "failed",
    "rejected",
    "needs_manual_changes",
    "pending",
    "missing",
    "timeline_safety_blocked",
    "timeline_safety_failed",
    "review_timeline_dashboard_blocked",
    "review_timeline_dashboard_failed",
    "final_quality_blocked",
    "final_quality_failed",
}

EXECUTION_FLAG_FRAGMENTS = (
    "can_apply",
    "can_execute",
    "can_reorder",
    "can_trim",
    "can_extend",
    "can_insert",
    "can_move",
    "can_split",
    "can_merge",
    "apply_changes",
    "remove_and_moments",
)


class RenderReadinessGuard:
    def evaluate(self, job: Any) -> RenderReadinessReport:
        job_id = str(self._get(job, "job_id", self._get(job, "id", "unknown")))

        checks = [
            self._check_review_timeline_plan_present(job),
            self._check_review_timeline_items_present(job),
            self._check_timeline_approval_approved(job),
            self._check_timeline_safety_passed(job),
            self._check_dashboard_package_ready(job),
            self._check_final_quality_available(job),
            self._check_final_quality_not_blocked(job),
            self._check_no_blocking_errors(job),
            self._check_no_render_permission_leaked(job),
            self._check_no_execution_permission_leaked(job),
            self._check_human_approval_chain_present(job),
            self._check_final_quality_score_reasonable(job),
            self._check_render_stage_not_started(job),
        ]

        return build_report_from_checks(
            job_id=job_id,
            checks=checks,
            metadata=dict(BLOCK8_METADATA),
        )

    def _check_review_timeline_plan_present(self, job: Any) -> RenderReadinessCheck:
        plan = self._dict(self._get(job, "review_timeline_plan"))
        report = self._dict(self._get(job, "review_timeline_plan_report"))
        status = self._status(
            self._get(job, "review_timeline_plan_status")
            or plan.get("status")
            or report.get("status")
        )

        if plan or report or status in READY_STATUSES:
            return self._passed(
                "review_timeline_plan_present",
                "Review Timeline Plan vorhanden",
                "block6_review_timeline",
                "Review Timeline Plan ist vorhanden.",
                {"status": status, "has_plan": bool(plan), "has_report": bool(report)},
            )

        return self._blocked(
            "review_timeline_plan_present",
            "Review Timeline Plan vorhanden",
            "block6_review_timeline",
            "Review Timeline Plan fehlt.",
            {"status": status, "has_plan": False, "has_report": False},
        )

    def _check_review_timeline_items_present(self, job: Any) -> RenderReadinessCheck:
        items = self._timeline_items(job)

        if items:
            return self._passed(
                "review_timeline_items_present",
                "Review Timeline Items vorhanden",
                "block6_review_timeline",
                "Review Timeline enth?lt Items.",
                {"item_count": len(items)},
            )

        return self._blocked(
            "review_timeline_items_present",
            "Review Timeline Items vorhanden",
            "block6_review_timeline",
            "Review Timeline Items fehlen.",
            {"item_count": 0},
        )

    def _check_timeline_approval_approved(self, job: Any) -> RenderReadinessCheck:
        gate = self._dict(self._get(job, "timeline_approval_gate"))
        report = self._dict(self._get(job, "timeline_approval_gate_report"))
        approval_status = self._status(
            self._get(job, "timeline_approval_status")
            or gate.get("approval_status")
            or gate.get("status")
            or report.get("approval_status")
            or report.get("status")
            or self._get(job, "timeline_approval_gate_status")
        )

        if approval_status == "approved":
            return self._passed(
                "timeline_approval_approved",
                "Timeline Approval approved",
                "approval",
                "Timeline Approval ist approved.",
                {"approval_status": approval_status},
            )

        return self._blocked(
            "timeline_approval_approved",
            "Timeline Approval approved",
            "approval",
            "Timeline Approval ist nicht approved.",
            {"approval_status": approval_status or None},
        )

    def _check_timeline_safety_passed(self, job: Any) -> RenderReadinessCheck:
        validator = self._dict(self._get(job, "timeline_safety_validator"))
        report = self._dict(self._get(job, "timeline_safety_validator_report"))
        status = self._status(
            self._get(job, "timeline_safety_validation_status")
            or validator.get("status")
            or report.get("status")
        )
        is_safe_future = self._truthy(
            self._get(job, "timeline_is_safe_for_future_execution")
            or validator.get("is_safe_for_future_execution")
            or report.get("is_safe_for_future_execution")
        )
        is_safe_for_render = self._truthy(
            self._get(job, "timeline_is_safe_for_render")
            or validator.get("is_safe_for_render")
            or report.get("is_safe_for_render")
        )
        blocking_errors = self._string_list(
            self._get(job, "timeline_safety_blocking_errors")
            or validator.get("blocking_errors")
            or report.get("blocking_errors")
        )

        if blocking_errors:
            return self._blocked(
                "timeline_safety_passed",
                "Timeline Safety passed oder safe",
                "safety",
                "Timeline Safety hat Blocking Errors.",
                {"status": status, "blocking_errors": blocking_errors},
            )

        if status in {"passed", "safe", "timeline_safety_passed", "timeline_safety_safe"} or is_safe_future or is_safe_for_render:
            return self._passed(
                "timeline_safety_passed",
                "Timeline Safety passed oder safe",
                "safety",
                "Timeline Safety ist passed oder safe.",
                {
                    "status": status,
                    "is_safe_for_future_execution": is_safe_future,
                    "is_safe_for_render": is_safe_for_render,
                },
            )

        return self._blocked(
            "timeline_safety_passed",
            "Timeline Safety passed oder safe",
            "safety",
            "Timeline Safety fehlt oder ist nicht safe.",
            {"status": status or None},
        )

    def _check_dashboard_package_ready(self, job: Any) -> RenderReadinessCheck:
        package = self._dict(self._get(job, "review_timeline_dashboard_package"))
        report = self._dict(self._get(job, "review_timeline_dashboard_package_report"))
        status = self._status(
            self._get(job, "review_timeline_dashboard_package_status")
            or package.get("status")
            or report.get("status")
        )
        blocking_errors = self._string_list(
            self._get(job, "review_timeline_dashboard_blocking_errors")
            or package.get("blocking_errors")
            or report.get("blocking_errors")
        )

        if blocking_errors:
            return self._blocked(
                "dashboard_package_ready",
                "Dashboard Package ready",
                "dashboard",
                "Dashboard Package hat Blocking Errors.",
                {"status": status, "blocking_errors": blocking_errors},
            )

        if package or report:
            if status in {"ready", "ready_with_warnings", "review_timeline_dashboard_ready", "review_timeline_dashboard_ready_with_warnings"}:
                return self._passed(
                    "dashboard_package_ready",
                    "Dashboard Package ready",
                    "dashboard",
                    "Dashboard Package ist ready.",
                    {"status": status},
                )

        return self._blocked(
            "dashboard_package_ready",
            "Dashboard Package ready",
            "dashboard",
            "Dashboard Package fehlt oder ist nicht ready.",
            {"status": status or None, "has_package": bool(package), "has_report": bool(report)},
        )

    def _check_final_quality_available(self, job: Any) -> RenderReadinessCheck:
        report = self._dict(self._get(job, "final_quality_validation_report"))
        validator = self._dict(self._get(job, "final_quality_validator"))

        if report or validator:
            return self._passed(
                "final_quality_available",
                "Final Quality vorhanden",
                "block7_final_quality",
                "Final Quality Report ist vorhanden.",
                {"has_report": bool(report), "has_validator": bool(validator)},
            )

        return self._blocked(
            "final_quality_available",
            "Final Quality vorhanden",
            "block7_final_quality",
            "Final Quality Report fehlt.",
            {"has_report": False, "has_validator": False},
        )

    def _check_final_quality_not_blocked(self, job: Any) -> RenderReadinessCheck:
        report = self._dict(self._get(job, "final_quality_validation_report"))
        status = self._status(
            self._get(job, "final_quality_validation_status")
            or report.get("status")
        )
        blocking_count = self._int(
            self._get(job, "final_quality_blocking_count")
            or report.get("blocking_count")
            or 0
        )
        blocking_reasons = self._string_list(
            self._get(job, "final_quality_blocking_reasons")
            or report.get("blocking_reasons")
        )

        if status in {"blocked", "failed", "final_quality_blocked", "final_quality_failed"} or blocking_count > 0 or blocking_reasons:
            return self._blocked(
                "final_quality_not_blocked",
                "Final Quality nicht blocked",
                "block7_final_quality",
                "Final Quality ist blocked oder hat Blocking Reasons.",
                {
                    "status": status,
                    "blocking_count": blocking_count,
                    "blocking_reasons": blocking_reasons,
                },
            )

        if report:
            return self._passed(
                "final_quality_not_blocked",
                "Final Quality nicht blocked",
                "block7_final_quality",
                "Final Quality ist nicht blocked.",
                {"status": status, "blocking_count": blocking_count},
            )

        return self._blocked(
            "final_quality_not_blocked",
            "Final Quality nicht blocked",
            "block7_final_quality",
            "Final Quality kann nicht gepr?ft werden, weil der Report fehlt.",
            {"status": status or None},
        )

    def _check_no_blocking_errors(self, job: Any) -> RenderReadinessCheck:
        blocking_sources = {
            "timeline_approval_blocking_reasons": self._string_list(self._get(job, "timeline_approval_blocking_reasons")),
            "timeline_safety_blocking_errors": self._string_list(self._get(job, "timeline_safety_blocking_errors")),
            "review_timeline_dashboard_blocking_errors": self._string_list(self._get(job, "review_timeline_dashboard_blocking_errors")),
            "final_quality_blocking_reasons": self._string_list(self._get(job, "final_quality_blocking_reasons")),
        }
        found = {key: value for key, value in blocking_sources.items() if value}

        if found:
            return self._blocked(
                "no_blocking_errors",
                "Keine Blocking Errors",
                "safety",
                "Blocking Errors aus Block 6 oder Block 7 gefunden.",
                {"blocking_sources": found},
            )

        return self._passed(
            "no_blocking_errors",
            "Keine Blocking Errors",
            "safety",
            "Keine Blocking Errors aus Block 6 oder Block 7 gefunden.",
            {},
        )

    def _check_no_render_permission_leaked(self, job: Any) -> RenderReadinessCheck:
        leaks = self._find_truthy_keys(job, ("can_render",))

        if leaks:
            return self._blocked(
                "no_render_permission_leaked",
                "Keine alte Render-Freigabe ?bernommen",
                "permission_leak",
                "Ein altes can_render Feld ist True.",
                {"leaked_fields": leaks},
            )

        return self._passed(
            "no_render_permission_leaked",
            "Keine alte Render-Freigabe ?bernommen",
            "permission_leak",
            "Keine alte Render-Freigabe ist True.",
            {},
        )

    def _check_no_execution_permission_leaked(self, job: Any) -> RenderReadinessCheck:
        leaks = self._find_truthy_keys(job, EXECUTION_FLAG_FRAGMENTS)

        if leaks:
            return self._blocked(
                "no_execution_permission_leaked",
                "Keine alte Execution-Freigabe ?bernommen",
                "permission_leak",
                "Ein altes Execution-Feld ist True.",
                {"leaked_fields": leaks},
            )

        return self._passed(
            "no_execution_permission_leaked",
            "Keine alte Execution-Freigabe ?bernommen",
            "permission_leak",
            "Keine alte Execution-Freigabe ist True.",
            {},
        )

    def _check_human_approval_chain_present(self, job: Any) -> RenderReadinessCheck:
        approved_by = self._get(job, "timeline_approved_by")
        gate = self._dict(self._get(job, "timeline_approval_gate"))
        report = self._dict(self._get(job, "timeline_approval_gate_report"))
        approval_info = approved_by or gate.get("approved_by") or report.get("approved_by") or report.get("reviewed_by")

        if approval_info:
            return self._passed(
                "human_approval_chain_present",
                "Menschliche Approval-Kette vorhanden",
                "approval",
                "Menschliche Approval-Info ist vorhanden.",
                {"approval_info_present": True},
            )

        return self._warning(
            "human_approval_chain_present",
            "Menschliche Approval-Kette vorhanden",
            "approval",
            "Menschliche Approval-Info ist unklar.",
            {"approval_info_present": False},
        )

    def _check_final_quality_score_reasonable(self, job: Any) -> RenderReadinessCheck:
        report = self._dict(self._get(job, "final_quality_validation_report"))
        score = self._float(
            self._get(job, "final_quality_overall_score")
            if self._get(job, "final_quality_overall_score") is not None
            else report.get("overall_quality_score")
        )

        if score is None:
            return self._warning(
                "final_quality_score_reasonable",
                "Final Quality Score reasonable",
                "block7_final_quality",
                "Final Quality Score fehlt.",
                {"score": None, "minimum": 0.70},
            )

        if score >= 0.70:
            return self._passed(
                "final_quality_score_reasonable",
                "Final Quality Score reasonable",
                "block7_final_quality",
                "Final Quality Score ist ausreichend.",
                {"score": score, "minimum": 0.70},
            )

        return self._warning(
            "final_quality_score_reasonable",
            "Final Quality Score reasonable",
            "block7_final_quality",
            "Final Quality Score ist unter 0.70.",
            {"score": score, "minimum": 0.70},
        )

    def _check_render_stage_not_started(self, job: Any) -> RenderReadinessCheck:
        suspicious_fields = (
            "render_output",
            "render_output_path",
            "render_result",
            "render_status",
            "ffmpeg_result",
            "export" "_video_path",
            "rendered_video_path",
        )
        found: dict[str, Any] = {}

        for key in suspicious_fields:
            value = self._get(job, key)
            if value not in (None, "", {}, [], False):
                found[key] = value

        status = self._status(self._get(job, "status"))
        if status in {"rendered", "rendering", "exported"}:
            found["status"] = status

        if found:
            return self._blocked(
                "render_stage_not_started",
                "Render Stage noch nicht gestartet",
                "safety",
                "Render Stage scheint bereits unerwartet gestartet zu sein.",
                {"found": found},
            )

        return self._passed(
            "render_stage_not_started",
            "Render Stage noch nicht gestartet",
            "safety",
            "Keine gestartete Render Stage gefunden.",
            {},
        )

    def _passed(
        self,
        check_id: str,
        check_name: str,
        category: str,
        message: str,
        evidence: dict[str, Any],
    ) -> RenderReadinessCheck:
        return RenderReadinessCheck(
            check_id=check_id,
            check_name=check_name,
            category=category,
            status=CHECK_STATUS_PASSED,
            severity=SEVERITY_INFO,
            message=message,
            evidence=evidence,
            blocking=False,
            review_required=False,
            metadata=dict(BLOCK8_METADATA),
        )

    def _warning(
        self,
        check_id: str,
        check_name: str,
        category: str,
        message: str,
        evidence: dict[str, Any],
    ) -> RenderReadinessCheck:
        return RenderReadinessCheck(
            check_id=check_id,
            check_name=check_name,
            category=category,
            status=CHECK_STATUS_WARNING,
            severity=SEVERITY_WARNING,
            message=message,
            evidence=evidence,
            blocking=False,
            review_required=True,
            metadata=dict(BLOCK8_METADATA),
        )

    def _blocked(
        self,
        check_id: str,
        check_name: str,
        category: str,
        message: str,
        evidence: dict[str, Any],
    ) -> RenderReadinessCheck:
        return RenderReadinessCheck(
            check_id=check_id,
            check_name=check_name,
            category=category,
            status=CHECK_STATUS_BLOCKED,
            severity=SEVERITY_BLOCKING,
            message=message,
            evidence=evidence,
            blocking=True,
            review_required=True,
            metadata=dict(BLOCK8_METADATA),
        )

    def _timeline_items(self, job: Any) -> list[dict[str, Any]]:
        direct = self._list(self._get(job, "review_timeline_plan_items"))
        if direct:
            return direct

        plan = self._dict(self._get(job, "review_timeline_plan"))
        report = self._dict(self._get(job, "review_timeline_plan_report"))

        for source in (plan, report):
            for key in ("items", "timeline_items", "plan_items"):
                items = self._list(source.get(key))
                if items:
                    return items

        return []

    def _find_truthy_keys(self, job: Any, fragments: tuple[str, ...]) -> list[str]:
        data = self._job_mapping(job)
        leaked: list[str] = []

        for key, value in data.items():
            lower_key = str(key).lower()
            if lower_key.startswith("render_readiness_"):
                continue
            if any(fragment in lower_key for fragment in fragments) and self._truthy(value):
                leaked.append(str(key))

        return sorted(leaked)

    def _job_mapping(self, job: Any) -> dict[str, Any]:
        if isinstance(job, dict):
            return dict(job)

        mapping: dict[str, Any] = {}
        for key in dir(job):
            if key.startswith("_"):
                continue
            try:
                value = getattr(job, key)
            except Exception:
                continue
            if callable(value):
                continue
            mapping[key] = value
        return mapping

    def _get(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _dict(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _list(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

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

    def _status(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().lower()

    def _truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "approved", "ready", "safe", "passed"}
        return bool(value)

    def _int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _float(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


def evaluate_render_readiness(job: Any) -> RenderReadinessReport:
    return RenderReadinessGuard().evaluate(job)
