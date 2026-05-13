from __future__ import annotations

from typing import Any

from models.review_timeline_plan import (
    REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY,
    REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
    REVIEW_TIMELINE_ACTION_REMOVE_REVIEW,
    REVIEW_TIMELINE_ACTION_TRIM_REVIEW,
    REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED,
    REVIEW_TIMELINE_PROTECTION_CONTINUITY_BLOCKED,
    REVIEW_TIMELINE_PROTECTION_PROTECTED,
    ReviewTimelineItem,
    ReviewTimelinePlan,
)
from models.timeline_approval_gate import TIMELINE_APPROVAL_STATUS_APPROVED
from models.timeline_safety_validator import (
    TIMELINE_SAFETY_REASON_APPROVAL_OVERRIDDEN_BY_SAFETY_VALIDATOR,
    TIMELINE_SAFETY_REASON_CENSOR_ITEM_NOT_PROTECTED,
    TIMELINE_SAFETY_REASON_CONTINUITY_BLOCK_NOT_PRESERVED,
    TIMELINE_SAFETY_REASON_END_BEFORE_START,
    TIMELINE_SAFETY_REASON_EXECUTION_NOT_SAFE,
    TIMELINE_SAFETY_REASON_INVALID_SOURCE_TIMING,
    TIMELINE_SAFETY_REASON_MISSING_REVIEW_TIMELINE_ITEMS,
    TIMELINE_SAFETY_REASON_MISSING_REVIEW_TIMELINE_PLAN,
    TIMELINE_SAFETY_REASON_NEGATIVE_END_TIME,
    TIMELINE_SAFETY_REASON_NEGATIVE_START_TIME,
    TIMELINE_SAFETY_REASON_PROTECTED_ITEM_HAS_UNSAFE_ACTION,
    TIMELINE_SAFETY_REASON_REMOVE_REVIEW_WITHOUT_HUMAN_REVIEW_SAFETY,
    TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34,
    TIMELINE_SAFETY_REASON_TIMELINE_GAP,
    TIMELINE_SAFETY_REASON_TIMELINE_OVERLAP,
    TIMELINE_SAFETY_REASON_TRIM_REVIEW_WITHOUT_HUMAN_REVIEW_SAFETY,
    TIMELINE_SAFETY_REASON_ZERO_OR_NEGATIVE_DURATION,
    TIMELINE_SAFETY_STATUS_BLOCKED,
    TIMELINE_SAFETY_STATUS_FAILED,
    TIMELINE_SAFETY_STATUS_PASSED,
    TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS,
    TimelineSafetyItemResult,
    TimelineSafetyValidation,
    TimelineSafetyValidatorRunReport,
)


SMALL_GAP_WARNING_SECONDS = 0.25


class TimelineSafetyValidator:
    source = "timeline_safety_validator"

    def validate(
        self,
        job: Any | None,
    ) -> TimelineSafetyValidatorRunReport:
        try:
            validation = self._validate_job(job)

            return TimelineSafetyValidatorRunReport(
                status=validation.validation_status,
                timeline_safety_validation=validation,
                validation_status=validation.validation_status,
                is_safe_for_future_execution=(
                    validation.is_safe_for_future_execution
                ),
                is_safe_for_render=False,
                requires_manual_review=validation.requires_manual_review,
                blocking_errors=list(validation.blocking_errors or []),
                warnings=list(validation.warnings or []),
                errors=[],
                metadata={
                    "source": self.source,
                    "job_id": validation.job_id,
                },
            )
        except Exception as exc:
            validation = TimelineSafetyValidation(
                job_id=self._get_value(job, "job_id"),
                validation_status=TIMELINE_SAFETY_STATUS_FAILED,
                is_safe_for_future_execution=False,
                is_safe_for_render=False,
                requires_manual_review=True,
                blocking_errors=[TIMELINE_SAFETY_STATUS_FAILED],
                warnings=[],
                metadata={
                    "source": self.source,
                    "error": str(exc),
                },
            )

            return TimelineSafetyValidatorRunReport(
                status=TIMELINE_SAFETY_STATUS_FAILED,
                timeline_safety_validation=validation,
                validation_status=TIMELINE_SAFETY_STATUS_FAILED,
                is_safe_for_future_execution=False,
                is_safe_for_render=False,
                requires_manual_review=True,
                blocking_errors=list(validation.blocking_errors or []),
                warnings=[],
                errors=[str(exc)],
                metadata={
                    "source": self.source,
                    "job_id": validation.job_id,
                },
            )

    def _validate_job(self, job: Any | None) -> TimelineSafetyValidation:
        job_id = self._get_value(job, "job_id") or self._get_value(job, "id")

        plan = self._extract_review_timeline_plan(job)
        items = self._extract_review_timeline_items(job, plan)

        approval_gate_id = self._extract_approval_gate_id(job)
        approval_status = str(
            self._get_value(job, "timeline_approval_status") or ""
        )
        can_proceed_to_execution = bool(
            self._get_value(job, "timeline_can_proceed_to_execution")
        )
        can_render = bool(self._get_value(job, "timeline_can_render"))

        validation = TimelineSafetyValidation(
            job_id=job_id,
            source_review_timeline_plan_id=(
                plan.plan_id if plan is not None else None
            ),
            source_timeline_approval_gate_id=approval_gate_id,
            is_safe_for_future_execution=False,
            is_safe_for_render=False,
            requires_manual_review=True,
            metadata={
                "source": self.source,
                "approval_status": approval_status,
                "can_proceed_to_execution": can_proceed_to_execution,
                "can_render": can_render,
            },
        )

        if plan is None:
            self._add_blocking_error(
                validation,
                TIMELINE_SAFETY_REASON_MISSING_REVIEW_TIMELINE_PLAN,
            )

        if not items:
            self._add_blocking_error(
                validation,
                TIMELINE_SAFETY_REASON_MISSING_REVIEW_TIMELINE_ITEMS,
            )

        if can_render:
            self._add_blocking_error(
                validation,
                TIMELINE_SAFETY_REASON_RENDER_NOT_ALLOWED_IN_2B_34,
            )
            validation.approval_violation_count += 1

        if items:
            self._validate_items(validation, items)

        if (
            approval_status == TIMELINE_APPROVAL_STATUS_APPROVED
            and validation.blocking_errors
        ):
            self._add_blocking_error(
                validation,
                TIMELINE_SAFETY_REASON_APPROVAL_OVERRIDDEN_BY_SAFETY_VALIDATOR,
            )
            validation.approval_violation_count += 1

        if can_proceed_to_execution and validation.blocking_errors:
            self._add_blocking_error(
                validation,
                TIMELINE_SAFETY_REASON_EXECUTION_NOT_SAFE,
            )
            validation.approval_violation_count += 1

        self._finish_validation(validation, items, approval_status)

        return validation

    def _validate_items(
        self,
        validation: TimelineSafetyValidation,
        items: list[ReviewTimelineItem],
    ) -> None:
        sorted_items = sorted(
            items,
            key=lambda item: float(item.start_seconds or 0.0),
        )

        previous_end: float | None = None

        for index, item in enumerate(sorted_items):
            result = self._validate_single_item(index, item)
            validation.item_results.append(result)

            for error in result.blocking_errors:
                self._add_blocking_error(validation, error)

            for warning in result.warnings:
                self._add_warning(validation, warning)

            self._increase_counters_from_result(validation, result)

            start = self._as_float(item.start_seconds)
            end = self._as_float(item.end_seconds)

            if previous_end is not None and start is not None:
                gap = round(start - previous_end, 6)

                if gap < 0:
                    self._add_blocking_error(
                        validation,
                        TIMELINE_SAFETY_REASON_TIMELINE_OVERLAP,
                    )
                    validation.overlap_count += 1

                if gap > 0 and gap <= SMALL_GAP_WARNING_SECONDS:
                    self._add_warning(
                        validation,
                        TIMELINE_SAFETY_REASON_TIMELINE_GAP,
                    )
                    validation.gap_count += 1

                if gap > SMALL_GAP_WARNING_SECONDS:
                    self._add_blocking_error(
                        validation,
                        TIMELINE_SAFETY_REASON_TIMELINE_GAP,
                    )
                    validation.gap_count += 1

            if end is not None:
                previous_end = end

    def _validate_single_item(
        self,
        index: int,
        item: ReviewTimelineItem,
    ) -> TimelineSafetyItemResult:
        start = self._as_float(item.start_seconds)
        end = self._as_float(item.end_seconds)
        duration = self._as_float(item.duration_seconds)
        source_start = self._as_float(item.source_start_seconds)
        source_end = self._as_float(item.source_end_seconds)

        result = TimelineSafetyItemResult(
            item_index=index,
            item_id=item.timeline_item_id,
            action=item.action,
            protection_status=item.protection_status,
            start_seconds=start,
            end_seconds=end,
            duration_seconds=duration,
            source_start_seconds=source_start,
            source_end_seconds=source_end,
            metadata={
                "review_required": bool(item.review_required),
                "review_reason": item.review_reason,
                "safety_flags": list(item.safety_flags or []),
                "censor_sfx_required": bool(item.censor_sfx_required),
                "continuity_blocked": bool(item.continuity_blocked),
            },
        )

        if start is None or end is None or duration is None:
            result.blocking_errors.append(
                TIMELINE_SAFETY_REASON_INVALID_SOURCE_TIMING
            )

        if start is not None and start < 0:
            result.blocking_errors.append(
                TIMELINE_SAFETY_REASON_NEGATIVE_START_TIME
            )

        if end is not None and end < 0:
            result.blocking_errors.append(
                TIMELINE_SAFETY_REASON_NEGATIVE_END_TIME
            )

        if start is not None and end is not None and end < start:
            result.blocking_errors.append(
                TIMELINE_SAFETY_REASON_END_BEFORE_START
            )

        if duration is not None and duration <= 0:
            result.blocking_errors.append(
                TIMELINE_SAFETY_REASON_ZERO_OR_NEGATIVE_DURATION
            )

        if source_start is not None and source_start < 0:
            result.blocking_errors.append(
                TIMELINE_SAFETY_REASON_INVALID_SOURCE_TIMING
            )

        if (
            source_start is not None
            and source_end is not None
            and source_end < source_start
        ):
            result.blocking_errors.append(
                TIMELINE_SAFETY_REASON_INVALID_SOURCE_TIMING
            )

        if self._is_protected(item) and item.action in {
            REVIEW_TIMELINE_ACTION_REMOVE_REVIEW,
            REVIEW_TIMELINE_ACTION_TRIM_REVIEW,
        }:
            result.blocking_errors.append(
                TIMELINE_SAFETY_REASON_PROTECTED_ITEM_HAS_UNSAFE_ACTION
            )

        if self._is_censor_item(item) and not self._has_valid_censor_safety(item):
            result.blocking_errors.append(
                TIMELINE_SAFETY_REASON_CENSOR_ITEM_NOT_PROTECTED
            )

        if self._is_continuity_item(item) and not self._has_valid_continuity_safety(item):
            result.blocking_errors.append(
                TIMELINE_SAFETY_REASON_CONTINUITY_BLOCK_NOT_PRESERVED
            )

        if (
            item.action == REVIEW_TIMELINE_ACTION_REMOVE_REVIEW
            and not self._has_human_review_safety(item)
        ):
            result.blocking_errors.append(
                TIMELINE_SAFETY_REASON_REMOVE_REVIEW_WITHOUT_HUMAN_REVIEW_SAFETY
            )

        if (
            item.action == REVIEW_TIMELINE_ACTION_TRIM_REVIEW
            and not self._has_human_review_safety(item)
        ):
            result.blocking_errors.append(
                TIMELINE_SAFETY_REASON_TRIM_REVIEW_WITHOUT_HUMAN_REVIEW_SAFETY
            )

        result.is_valid = not bool(result.blocking_errors)

        return result

    def _finish_validation(
        self,
        validation: TimelineSafetyValidation,
        items: list[ReviewTimelineItem],
        approval_status: str,
    ) -> None:
        validation.total_items_checked = len(items or [])
        validation.is_safe_for_render = False

        has_continuity_blocks = any(self._is_continuity_item(item) for item in items)
        has_censor_review_open = any(self._is_censor_item(item) for item in items)

        if validation.blocking_errors:
            validation.validation_status = TIMELINE_SAFETY_STATUS_BLOCKED
            validation.is_safe_for_future_execution = False
            validation.requires_manual_review = True
            validation.future_execution_safety_status = "blocked"
            return

        if validation.warnings:
            validation.validation_status = (
                TIMELINE_SAFETY_STATUS_PASSED_WITH_WARNINGS
            )
        else:
            validation.validation_status = TIMELINE_SAFETY_STATUS_PASSED

        validation.is_safe_for_future_execution = (
            approval_status == TIMELINE_APPROVAL_STATUS_APPROVED
            and not has_continuity_blocks
            and not has_censor_review_open
        )
        validation.requires_manual_review = not validation.is_safe_for_future_execution
        validation.future_execution_safety_status = (
            "safe_after_approval"
            if validation.is_safe_for_future_execution
            else "requires_approval_or_review"
        )

    def _increase_counters_from_result(
        self,
        validation: TimelineSafetyValidation,
        result: TimelineSafetyItemResult,
    ) -> None:
        errors = set(result.blocking_errors or [])

        if TIMELINE_SAFETY_REASON_INVALID_SOURCE_TIMING in errors:
            validation.invalid_timing_count += 1

        if (
            TIMELINE_SAFETY_REASON_NEGATIVE_START_TIME in errors
            or TIMELINE_SAFETY_REASON_NEGATIVE_END_TIME in errors
        ):
            validation.negative_time_count += 1

        if TIMELINE_SAFETY_REASON_END_BEFORE_START in errors:
            validation.invalid_timing_count += 1

        if TIMELINE_SAFETY_REASON_ZERO_OR_NEGATIVE_DURATION in errors:
            validation.zero_or_negative_duration_count += 1

        if TIMELINE_SAFETY_REASON_PROTECTED_ITEM_HAS_UNSAFE_ACTION in errors:
            validation.protected_violation_count += 1

        if TIMELINE_SAFETY_REASON_CENSOR_ITEM_NOT_PROTECTED in errors:
            validation.censor_violation_count += 1

        if TIMELINE_SAFETY_REASON_CONTINUITY_BLOCK_NOT_PRESERVED in errors:
            validation.continuity_violation_count += 1

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
        if isinstance(raw_report, dict) and raw_report:
            report_plan = raw_report.get("review_timeline_plan")
            if isinstance(report_plan, dict) and report_plan:
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

    def _extract_approval_gate_id(self, job: Any | None) -> str | None:
        raw_gate = self._get_value(job, "timeline_approval_gate")

        if isinstance(raw_gate, dict):
            return raw_gate.get("approval_gate_id")

        if raw_gate is not None and hasattr(raw_gate, "approval_gate_id"):
            return raw_gate.approval_gate_id

        raw_report = self._get_value(job, "timeline_approval_gate_report")
        if isinstance(raw_report, dict):
            gate = raw_report.get("timeline_approval_gate")
            if isinstance(gate, dict):
                return gate.get("approval_gate_id")

        return self._get_value(job, "timeline_approval_gate_id")

    def _is_protected(self, item: ReviewTimelineItem) -> bool:
        return item.protection_status in {
            REVIEW_TIMELINE_PROTECTION_PROTECTED,
            REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED,
            REVIEW_TIMELINE_PROTECTION_CONTINUITY_BLOCKED,
        }

    def _is_censor_item(self, item: ReviewTimelineItem) -> bool:
        return (
            bool(item.censor_sfx_required)
            or item.protection_status == REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED
            or item.action == REVIEW_TIMELINE_ACTION_CENSOR_KEEP
        )

    def _has_valid_censor_safety(self, item: ReviewTimelineItem) -> bool:
        return (
            bool(item.censor_sfx_required)
            and item.protection_status == REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED
            and item.action == REVIEW_TIMELINE_ACTION_CENSOR_KEEP
        )

    def _is_continuity_item(self, item: ReviewTimelineItem) -> bool:
        return (
            bool(item.continuity_blocked)
            or item.protection_status == REVIEW_TIMELINE_PROTECTION_CONTINUITY_BLOCKED
            or item.action == REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY
        )

    def _has_valid_continuity_safety(self, item: ReviewTimelineItem) -> bool:
        return (
            bool(item.continuity_blocked)
            and (
                item.action == REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY
                or item.protection_status
                == REVIEW_TIMELINE_PROTECTION_CONTINUITY_BLOCKED
            )
        )

    def _has_human_review_safety(self, item: ReviewTimelineItem) -> bool:
        flags = set(str(flag) for flag in list(item.safety_flags or []))
        metadata = dict(item.metadata or {})
        metadata_flags = set(
            str(flag) for flag in list(metadata.get("safety_flags") or [])
        )

        combined_flags = flags | metadata_flags

        return bool(
            {"review_only", "human_review", "requires_human_review"}
            & combined_flags
        )

    def _add_blocking_error(
        self,
        validation: TimelineSafetyValidation,
        error: str,
    ) -> None:
        if error not in validation.blocking_errors:
            validation.blocking_errors.append(error)

    def _add_warning(
        self,
        validation: TimelineSafetyValidation,
        warning: str,
    ) -> None:
        if warning not in validation.warnings:
            validation.warnings.append(warning)

    def _as_float(self, value: Any) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _get_value(self, source: Any | None, key: str) -> Any:
        if source is None:
            return None

        if isinstance(source, dict):
            return source.get(key)

        return getattr(source, key, None)
