from __future__ import annotations

from typing import Any

from models.review_timeline_dashboard_package import (
    REVIEW_TIMELINE_DASHBOARD_ACTION_APPROVE_TIMELINE,
    REVIEW_TIMELINE_DASHBOARD_ACTION_REJECT_TIMELINE,
    REVIEW_TIMELINE_DASHBOARD_ACTION_REQUEST_CHANGES,
    REVIEW_TIMELINE_DASHBOARD_ACTION_REVIEW_TIMELINE,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY,
    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY_WITH_WARNINGS,
    REVIEW_TIMELINE_DASHBOARD_SEVERITY_BLOCKING,
    REVIEW_TIMELINE_DASHBOARD_SEVERITY_HIGH,
    REVIEW_TIMELINE_DASHBOARD_SEVERITY_LOW,
    REVIEW_TIMELINE_DASHBOARD_SEVERITY_MEDIUM,
    ReviewTimelineDashboardItemCard,
    ReviewTimelineDashboardPackage,
    ReviewTimelineDashboardPackageRunReport,
)
from models.review_timeline_plan import (
    REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY,
    REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
    REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
    REVIEW_TIMELINE_ACTION_PROTECT,
    REVIEW_TIMELINE_ACTION_REMOVE_REVIEW,
    REVIEW_TIMELINE_ACTION_TECHNICAL_REVIEW,
    REVIEW_TIMELINE_ACTION_TRIM_REVIEW,
    REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED,
    REVIEW_TIMELINE_PROTECTION_CONTINUITY_BLOCKED,
    REVIEW_TIMELINE_PROTECTION_PROTECTED,
    ReviewTimelineItem,
    ReviewTimelinePlan,
)
from models.timeline_approval_gate import TimelineApprovalGate
from models.timeline_safety_validator import (
    TimelineSafetyItemResult,
    TimelineSafetyValidation,
)


class ReviewTimelineDashboardPackageBuilder:
    source = "review_timeline_dashboard_package_builder"

    def build(
        self,
        job: Any | None,
    ) -> ReviewTimelineDashboardPackageRunReport:
        try:
            package = self._build_package(job)

            return ReviewTimelineDashboardPackageRunReport(
                status=package.package_status,
                dashboard_package=package,
                review_status=package.review_status,
                approval_status=package.approval_status,
                safety_status=package.safety_status,
                can_proceed_to_execution=package.can_proceed_to_execution,
                can_render=False,
                requires_manual_review=package.requires_manual_review,
                warnings=list(package.warnings or []),
                blocking_errors=list(package.blocking_errors or []),
                errors=[],
                metadata={
                    "source": self.source,
                    "job_id": package.job_id,
                    "dashboard_only": True,
                    "media_unchanged": True,
                },
            )

        except Exception as exc:
            job_id = self._get_value(job, "job_id") or self._get_value(job, "id")

            package = ReviewTimelineDashboardPackage(
                job_id=job_id,
                package_status=REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED,
                review_status="failed",
                approval_status="failed",
                safety_status="failed",
                can_proceed_to_execution=False,
                can_render=False,
                is_safe_for_future_execution=False,
                is_safe_for_render=False,
                requires_manual_review=True,
                warnings=[],
                blocking_errors=[
                    REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED,
                ],
                dashboard_actions=[
                    REVIEW_TIMELINE_DASHBOARD_ACTION_REVIEW_TIMELINE,
                    REVIEW_TIMELINE_DASHBOARD_ACTION_REQUEST_CHANGES,
                    REVIEW_TIMELINE_DASHBOARD_ACTION_REJECT_TIMELINE,
                ],
                metadata={
                    "source": self.source,
                    "error": str(exc),
                    "dashboard_only": True,
                    "media_unchanged": True,
                    "no_execution_in_2b_35": True,
                },
            )

            return ReviewTimelineDashboardPackageRunReport(
                status=REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_FAILED,
                dashboard_package=package,
                review_status="failed",
                approval_status="failed",
                safety_status="failed",
                can_proceed_to_execution=False,
                can_render=False,
                requires_manual_review=True,
                warnings=[],
                blocking_errors=list(package.blocking_errors or []),
                errors=[str(exc)],
                metadata={
                    "source": self.source,
                    "job_id": job_id,
                },
            )

    def _build_package(self, job: Any | None) -> ReviewTimelineDashboardPackage:
        job_id = self._get_value(job, "job_id") or self._get_value(job, "id")

        plan = self._extract_review_timeline_plan(job)
        items = self._extract_review_timeline_items(job, plan)

        approval_gate = self._extract_timeline_approval_gate(job)
        safety_validation = self._extract_timeline_safety_validation(job)

        safety_item_results = self._extract_safety_item_results(
            job,
            safety_validation,
        )

        blocking_errors = self._collect_blocking_errors(
            job,
            approval_gate,
            safety_validation,
        )
        warnings = self._collect_warnings(
            job,
            approval_gate,
            safety_validation,
            plan,
        )

        review_status = self._extract_review_status(job, plan)
        approval_status = self._extract_approval_status(job, approval_gate)
        safety_status = self._extract_safety_status(job, safety_validation)

        can_proceed_to_execution = bool(
            self._get_value(job, "timeline_can_proceed_to_execution")
            or self._get_value(approval_gate, "can_proceed_to_execution")
        )

        is_safe_for_future_execution = bool(
            self._get_value(job, "timeline_is_safe_for_future_execution")
            or self._get_value(
                safety_validation,
                "is_safe_for_future_execution",
            )
        )

        requires_manual_review = bool(
            self._get_value(job, "timeline_safety_requires_manual_review")
            or self._get_value(
                safety_validation,
                "requires_manual_review",
            )
            or self._get_value(
                approval_gate,
                "requires_human_approval",
            )
            or blocking_errors
            or review_status == "pending_review"
            or approval_status != "approved"
        )

        summary = self._build_summary(
            plan=plan,
            items=items,
            safety_validation=safety_validation,
            warnings=warnings,
            blocking_errors=blocking_errors,
        )

        item_cards = self._build_item_cards(
            items=items,
            safety_item_results=safety_item_results,
        )

        package_status = self._resolve_package_status(
            blocking_errors=blocking_errors,
            warnings=warnings,
            item_cards=item_cards,
            plan=plan,
        )

        dashboard_actions = self._resolve_dashboard_actions(
            approval_status=approval_status,
            blocking_errors=blocking_errors,
            requires_manual_review=requires_manual_review,
        )

        package = ReviewTimelineDashboardPackage(
            job_id=job_id,
            package_status=package_status,
            source_review_timeline_plan_id=(
                self._get_value(plan, "plan_id")
                or self._get_value(job, "review_timeline_plan_id")
            ),
            source_timeline_approval_gate_id=(
                self._get_value(approval_gate, "approval_gate_id")
                or self._get_value(job, "timeline_approval_gate_id")
            ),
            source_timeline_safety_validation_id=(
                self._get_value(safety_validation, "safety_validation_id")
                or self._get_value(job, "timeline_safety_validation_id")
            ),
            review_status=review_status,
            approval_status=approval_status,
            safety_status=safety_status,
            can_proceed_to_execution=(
                can_proceed_to_execution
                and is_safe_for_future_execution
                and not blocking_errors
            ),
            can_render=False,
            is_safe_for_future_execution=(
                is_safe_for_future_execution and not blocking_errors
            ),
            is_safe_for_render=False,
            requires_manual_review=requires_manual_review,
            summary=summary,
            counters=dict(summary),
            timeline_items=[item.to_dict() for item in items],
            item_cards=item_cards,
            approval_panel=self._build_approval_panel(
                approval_gate=approval_gate,
                approval_status=approval_status,
            ),
            safety_panel=self._build_safety_panel(
                safety_validation=safety_validation,
                safety_status=safety_status,
                warnings=warnings,
                blocking_errors=blocking_errors,
            ),
            warnings=warnings,
            blocking_errors=blocking_errors,
            dashboard_actions=dashboard_actions,
            metadata={
                "source": self.source,
                "dashboard_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_35": True,
                "no_render_in_2b_35": True,
                "can_render_forced_false_by_2b_35": True,
                "source_modules": [
                    "review_timeline_plan",
                    "timeline_approval_gate",
                    "timeline_safety_validator",
                ],
            },
        )

        package.enforce_dashboard_only_safety()
        return package

    def _build_summary(
        self,
        plan: ReviewTimelinePlan | None,
        items: list[ReviewTimelineItem],
        safety_validation: TimelineSafetyValidation | None,
        warnings: list[str],
        blocking_errors: list[str],
    ) -> dict[str, Any]:
        total_items = int(
            self._get_value(plan, "total_items")
            or self._get_value(safety_validation, "total_items_checked")
            or len(items)
        )

        total_duration_seconds = float(
            self._get_value(plan, "total_duration_seconds")
            or sum(float(item.duration_seconds or 0.0) for item in items)
        )

        return {
            "total_items": total_items,
            "total_duration_seconds": round(total_duration_seconds, 3),
            "review_required_count": int(
                self._get_value(plan, "review_required_count")
                or sum(1 for item in items if item.review_required)
            ),
            "protected_count": int(
                self._get_value(plan, "protected_count")
                or sum(1 for item in items if self._is_protected(item))
            ),
            "censor_required_count": int(
                self._get_value(plan, "censor_required_count")
                or sum(1 for item in items if item.censor_sfx_required)
            ),
            "continuity_blocked_count": int(
                self._get_value(plan, "continuity_blocked_count")
                or sum(1 for item in items if item.continuity_blocked)
            ),
            "blocking_error_count": len(blocking_errors or []),
            "warning_count": len(warnings or []),
            "invalid_timing_count": int(
                self._get_value(safety_validation, "invalid_timing_count") or 0
            ),
            "overlapping_item_count": int(
                self._get_value(safety_validation, "overlap_count") or 0
            ),
            "gap_count": int(
                self._get_value(safety_validation, "gap_count") or 0
            ),
            "protected_violation_count": int(
                self._get_value(
                    safety_validation,
                    "protected_violation_count",
                )
                or 0
            ),
            "censor_violation_count": int(
                self._get_value(safety_validation, "censor_violation_count")
                or 0
            ),
            "continuity_violation_count": int(
                self._get_value(
                    safety_validation,
                    "continuity_violation_count",
                )
                or 0
            ),
            "approval_violation_count": int(
                self._get_value(safety_validation, "approval_violation_count")
                or 0
            ),
        }

    def _build_item_cards(
        self,
        items: list[ReviewTimelineItem],
        safety_item_results: list[TimelineSafetyItemResult],
    ) -> list[ReviewTimelineDashboardItemCard]:
        safety_by_item_id: dict[str, TimelineSafetyItemResult] = {}

        for safety_result in safety_item_results:
            item_id = str(safety_result.item_id or "")
            if item_id:
                safety_by_item_id[item_id] = safety_result

        item_cards: list[ReviewTimelineDashboardItemCard] = []

        for item in items:
            safety_result = safety_by_item_id.get(str(item.timeline_item_id))

            item_warnings = list(
                self._get_value(safety_result, "warnings") or []
            )
            item_blocking_errors = list(
                self._get_value(safety_result, "blocking_errors") or []
            )

            item_cards.append(
                ReviewTimelineDashboardItemCard(
                    item_id=item.timeline_item_id,
                    source_segment_id=item.source_segment_id,
                    start_seconds=item.start_seconds,
                    end_seconds=item.end_seconds,
                    duration_seconds=item.duration_seconds,
                    source_start_seconds=item.source_start_seconds,
                    source_end_seconds=item.source_end_seconds,
                    action=item.action,
                    label=self._label_for_action(item.action),
                    badge=self._badge_for_item(
                        item=item,
                        blocking_errors=item_blocking_errors,
                        warnings=item_warnings,
                    ),
                    severity=self._severity_for_item(
                        item=item,
                        blocking_errors=item_blocking_errors,
                        warnings=item_warnings,
                    ),
                    final_decision=item.final_decision,
                    protection_status=item.protection_status,
                    review_required=item.review_required,
                    protected=self._is_protected(item),
                    censor_sfx_required=item.censor_sfx_required,
                    continuity_blocked=item.continuity_blocked,
                    safety_status=(
                        "blocked"
                        if item_blocking_errors
                        else "warning"
                        if item_warnings
                        else "ok"
                    ),
                    warnings=item_warnings,
                    blocking_errors=item_blocking_errors,
                    safety_flags=list(item.safety_flags or []),
                    notes=list(item.notes or []),
                    metadata={
                        "review_reason": item.review_reason,
                        "source_metadata": dict(item.metadata or {}),
                    },
                )
            )

        return item_cards

    def _build_approval_panel(
        self,
        approval_gate: TimelineApprovalGate | None,
        approval_status: str,
    ) -> dict[str, Any]:
        return {
            "approval_status": approval_status,
            "gate_status": str(
                self._get_value(approval_gate, "gate_status")
                or "pending_review"
            ),
            "can_proceed_to_execution": bool(
                self._get_value(
                    approval_gate,
                    "can_proceed_to_execution",
                )
            ),
            "can_render": False,
            "requires_human_approval": bool(
                self._get_value(
                    approval_gate,
                    "requires_human_approval",
                )
                if approval_gate is not None
                else True
            ),
            "blocking_reasons": list(
                self._get_value(approval_gate, "blocking_reasons") or []
            ),
            "warnings": list(
                self._get_value(approval_gate, "warnings") or []
            ),
            "approved_by": self._get_value(approval_gate, "approved_by"),
            "approved_at": self._get_value(approval_gate, "approved_at"),
            "rejected_by": self._get_value(approval_gate, "rejected_by"),
            "rejected_at": self._get_value(approval_gate, "rejected_at"),
            "manual_change_reason": self._get_value(
                approval_gate,
                "manual_change_reason",
            ),
        }

    def _build_safety_panel(
        self,
        safety_validation: TimelineSafetyValidation | None,
        safety_status: str,
        warnings: list[str],
        blocking_errors: list[str],
    ) -> dict[str, Any]:
        return {
            "validation_status": safety_status,
            "is_safe_for_future_execution": bool(
                self._get_value(
                    safety_validation,
                    "is_safe_for_future_execution",
                )
            ),
            "is_safe_for_render": False,
            "requires_manual_review": bool(
                self._get_value(
                    safety_validation,
                    "requires_manual_review",
                )
                if safety_validation is not None
                else True
            ),
            "future_execution_safety_status": str(
                self._get_value(
                    safety_validation,
                    "future_execution_safety_status",
                )
                or "unknown"
            ),
            "blocking_errors": list(blocking_errors or []),
            "warnings": list(warnings or []),
        }

    def _resolve_package_status(
        self,
        blocking_errors: list[str],
        warnings: list[str],
        item_cards: list[ReviewTimelineDashboardItemCard],
        plan: ReviewTimelinePlan | None,
    ) -> str:
        if plan is None or not item_cards:
            return REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED

        if blocking_errors:
            return REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_BLOCKED

        if warnings:
            return REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY_WITH_WARNINGS

        return REVIEW_TIMELINE_DASHBOARD_PACKAGE_STATUS_READY

    def _resolve_dashboard_actions(
        self,
        approval_status: str,
        blocking_errors: list[str],
        requires_manual_review: bool,
    ) -> list[str]:
        actions = [
            REVIEW_TIMELINE_DASHBOARD_ACTION_REVIEW_TIMELINE,
            REVIEW_TIMELINE_DASHBOARD_ACTION_REQUEST_CHANGES,
            REVIEW_TIMELINE_DASHBOARD_ACTION_REJECT_TIMELINE,
        ]

        if (
            not blocking_errors
            and requires_manual_review
            and approval_status != "approved"
        ):
            actions.insert(1, REVIEW_TIMELINE_DASHBOARD_ACTION_APPROVE_TIMELINE)

        return actions

    def _extract_review_timeline_plan(
        self,
        job: Any | None,
    ) -> ReviewTimelinePlan | None:
        raw_plan = self._get_value(job, "review_timeline_plan")

        if isinstance(raw_plan, ReviewTimelinePlan):
            return raw_plan

        if isinstance(raw_plan, dict) and raw_plan:
            return ReviewTimelinePlan.from_dict(raw_plan)

        raw_report = self._get_value(job, "review_timeline_plan_report")
        if isinstance(raw_report, dict):
            report_plan = raw_report.get("review_timeline_plan")
            if isinstance(report_plan, dict):
                return ReviewTimelinePlan.from_dict(report_plan)

        return None

    def _extract_review_timeline_items(
        self,
        job: Any | None,
        plan: ReviewTimelinePlan | None,
    ) -> list[ReviewTimelineItem]:
        raw_items = self._get_value(job, "review_timeline_plan_items")

        if isinstance(raw_items, list) and raw_items:
            return [
                ReviewTimelineItem.from_dict(item)
                for item in raw_items
                if isinstance(item, dict)
            ]

        if plan is not None:
            return list(plan.items or [])

        return []

    def _extract_timeline_approval_gate(
        self,
        job: Any | None,
    ) -> TimelineApprovalGate | None:
        raw_gate = self._get_value(job, "timeline_approval_gate")

        if isinstance(raw_gate, TimelineApprovalGate):
            return raw_gate

        if isinstance(raw_gate, dict) and raw_gate:
            return TimelineApprovalGate.from_dict(raw_gate)

        raw_report = self._get_value(job, "timeline_approval_gate_report")
        if isinstance(raw_report, dict):
            report_gate = raw_report.get("timeline_approval_gate")
            if isinstance(report_gate, dict):
                return TimelineApprovalGate.from_dict(report_gate)

        return None

    def _extract_timeline_safety_validation(
        self,
        job: Any | None,
    ) -> TimelineSafetyValidation | None:
        raw_validation = self._get_value(job, "timeline_safety_validator")

        if isinstance(raw_validation, TimelineSafetyValidation):
            return raw_validation

        if isinstance(raw_validation, dict) and raw_validation:
            return TimelineSafetyValidation.from_dict(raw_validation)

        raw_report = self._get_value(job, "timeline_safety_validator_report")
        if isinstance(raw_report, dict):
            report_validation = raw_report.get("timeline_safety_validation")
            if isinstance(report_validation, dict):
                return TimelineSafetyValidation.from_dict(report_validation)

        return None

    def _extract_safety_item_results(
        self,
        job: Any | None,
        safety_validation: TimelineSafetyValidation | None,
    ) -> list[TimelineSafetyItemResult]:
        raw_item_results = self._get_value(job, "timeline_safety_item_results")

        if isinstance(raw_item_results, list) and raw_item_results:
            return [
                TimelineSafetyItemResult.from_dict(item)
                for item in raw_item_results
                if isinstance(item, dict)
            ]

        if safety_validation is not None:
            return list(safety_validation.item_results or [])

        return []

    def _collect_blocking_errors(
        self,
        job: Any | None,
        approval_gate: TimelineApprovalGate | None,
        safety_validation: TimelineSafetyValidation | None,
    ) -> list[str]:
        errors: list[str] = []

        self._extend_unique(
            errors,
            self._get_value(job, "timeline_approval_blocking_reasons"),
        )
        self._extend_unique(
            errors,
            self._get_value(approval_gate, "blocking_reasons"),
        )
        self._extend_unique(
            errors,
            self._get_value(job, "timeline_safety_blocking_errors"),
        )
        self._extend_unique(
            errors,
            self._get_value(safety_validation, "blocking_errors"),
        )

        return errors

    def _collect_warnings(
        self,
        job: Any | None,
        approval_gate: TimelineApprovalGate | None,
        safety_validation: TimelineSafetyValidation | None,
        plan: ReviewTimelinePlan | None,
    ) -> list[str]:
        warnings: list[str] = []

        self._extend_unique(warnings, self._get_value(plan, "warnings"))
        self._extend_unique(
            warnings,
            self._get_value(job, "timeline_approval_warnings"),
        )
        self._extend_unique(warnings, self._get_value(approval_gate, "warnings"))
        self._extend_unique(
            warnings,
            self._get_value(job, "timeline_safety_warnings"),
        )
        self._extend_unique(
            warnings,
            self._get_value(safety_validation, "warnings"),
        )

        return warnings

    def _extract_review_status(
        self,
        job: Any | None,
        plan: ReviewTimelinePlan | None,
    ) -> str:
        return str(
            self._get_value(job, "review_timeline_plan_status")
            or self._get_value(plan, "status")
            or "pending_review"
        )

    def _extract_approval_status(
        self,
        job: Any | None,
        approval_gate: TimelineApprovalGate | None,
    ) -> str:
        return str(
            self._get_value(job, "timeline_approval_status")
            or self._get_value(approval_gate, "approval_status")
            or "pending_review"
        )

    def _extract_safety_status(
        self,
        job: Any | None,
        safety_validation: TimelineSafetyValidation | None,
    ) -> str:
        return str(
            self._get_value(job, "timeline_safety_validation_status")
            or self._get_value(safety_validation, "validation_status")
            or "unknown"
        )

    def _label_for_action(self, action: str) -> str:
        labels = {
            REVIEW_TIMELINE_ACTION_KEEP_REVIEW: "Keep Review",
            REVIEW_TIMELINE_ACTION_TRIM_REVIEW: "Trim Review",
            REVIEW_TIMELINE_ACTION_REMOVE_REVIEW: "Remove Review",
            REVIEW_TIMELINE_ACTION_PROTECT: "Protected",
            REVIEW_TIMELINE_ACTION_CENSOR_KEEP: "Censor Keep",
            REVIEW_TIMELINE_ACTION_TECHNICAL_REVIEW: "Technical Review",
            REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY: (
                "Blocked By Continuity"
            ),
        }

        return labels.get(str(action or ""), "Unknown Review")

    def _badge_for_item(
        self,
        item: ReviewTimelineItem,
        blocking_errors: list[str],
        warnings: list[str],
    ) -> str:
        if blocking_errors:
            return "Blocked"

        if item.continuity_blocked:
            return "Continuity Blocked"

        if item.censor_sfx_required:
            return "Censor Required"

        if self._is_protected(item):
            return "Protected"

        if item.review_required:
            return "Review Required"

        if warnings:
            return "Warning"

        return "Ready"

    def _severity_for_item(
        self,
        item: ReviewTimelineItem,
        blocking_errors: list[str],
        warnings: list[str],
    ) -> str:
        if blocking_errors:
            return REVIEW_TIMELINE_DASHBOARD_SEVERITY_BLOCKING

        if item.continuity_blocked:
            return REVIEW_TIMELINE_DASHBOARD_SEVERITY_HIGH

        if item.censor_sfx_required:
            return REVIEW_TIMELINE_DASHBOARD_SEVERITY_HIGH

        if item.review_required:
            return REVIEW_TIMELINE_DASHBOARD_SEVERITY_MEDIUM

        if warnings:
            return REVIEW_TIMELINE_DASHBOARD_SEVERITY_MEDIUM

        return REVIEW_TIMELINE_DASHBOARD_SEVERITY_LOW

    def _is_protected(self, item: ReviewTimelineItem) -> bool:
        return item.protection_status in {
            REVIEW_TIMELINE_PROTECTION_PROTECTED,
            REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED,
            REVIEW_TIMELINE_PROTECTION_CONTINUITY_BLOCKED,
        }

    def _extend_unique(
        self,
        target: list[str],
        values: Any,
    ) -> None:
        for value in list(values or []):
            value_text = str(value)
            if value_text and value_text not in target:
                target.append(value_text)

    def _get_value(self, source: Any | None, key: str) -> Any:
        if source is None:
            return None

        if isinstance(source, dict):
            return source.get(key)

        return getattr(source, key, None)